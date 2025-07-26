#!/usr/bin/env python3
"""
Confluence XHTML to Markdown Converter

This script converts Confluence XHTML export to clean Markdown,
handling special cases like:
- CDATA sections in code blocks
- Tables with colspan and rowspan attributes
- Structured macros and other Confluence-specific elements
"""

import re
import sys
import os
from itertools import chain
import argparse
from bs4 import BeautifulSoup, Tag, NavigableString
from bs4.element import CData
import logging

# Global variable to store input file path
INPUT_FILE_PATH = ""

# Hidden characters constants
ZWSP = '\u200b'  # Zero Width Space
LRM = '\u200e'   # Left-to-Right Mark
HANGUL_FILLER = '\u3164'  # Hangul Filler


def backtick_curly_braces(text):
    """
    Wrap text embraced by curly braces with backticks.

    If there are 20 or fewer word characters (including spaces, Korean characters,
    alphabets, etc.) between the curly braces, format as `{...}`.

    Args:
        text (str): The input text to process.

    Returns:
        str: The processed text with curly braces content wrapped in backticks.
    """
    # \u2026 is the ellipsis character, `...` which is often used in Confluence
    pattern = r'(\{\{?[\w\s\-\|\u2026]{1,60}\}\}?)'
    return re.sub(pattern, r'`\1`', text)

def as_markdown(node):
    if isinstance(node, NavigableString):
        # This is a leaf node with text
        text = (
            node.replace('\u00A0', ' ') # Replace NBSP with space
            .replace('\n', ' ')  # Replace newlines with space
        )
        # Encode < and > to prevent conflict with JSX syntax.
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        # Normalize multiple spaces to a single space
        text = re.sub(r'\s+', ' ', text)
        if node.parent.name == 'code':
            # Do not backtick_curly_braces if the parent node is `<code>`, as it is backticked already.
            pass
        else:
            text = backtick_curly_braces(text)
        return text
    else:
        # Fatal error and crash
        raise TypeError(f"as_markdown() expects a NavigableString, got: {type(node).__name__}")

def ancestors(node):
    max_depth = 20
    stack = []
    current = node.parent
    while current and len(stack) < max_depth:
        stack.append(f'<{current.name}>')
        current = current.parent
    return ''.join(reversed(stack))

def print_node_with_properties(node):
    """
    Print all properties of a BeautifulSoup node in the format:
    <{node.name} property="{property.value}">

    Args:
        node: A BeautifulSoup Tag object

    Returns:
        A string representation of the node with all its properties
    """
    if not hasattr(node, 'name'):
        return str(node)

    # Start with the node name
    result = f"<{node.name}"

    # Add all attributes
    for attr_name, attr_value in node.attrs.items():
        # Handle different types of attribute values
        if isinstance(attr_value, list):
            # For list attributes like class, join with space
            attr_value = ' '.join(attr_value)
        elif isinstance(attr_value, bool) and attr_value:
            # For boolean attributes that are True, just include the name
            result += f" {attr_name}"
            continue

        # Add the attribute to the result
        result += f" {attr_name}=\"{attr_value}\""

    # Close the tag
    result += ">"

    return result

class SingleLineParser:
    def __init__(self, node):
        self.node = node
        self.markdown_lines = []

    @property
    def as_markdown(self):
        """Convert the node to Markdown format."""
        self.convert_recursively(self.node)
        # Join all lines without a space, and remove leading/trailing whitespace
        # It is supposed to preserve whitespace in the middle of the text
        return "".join(self.markdown_lines).strip()

    def convert_recursively(self, node):
        """Recursively convert child nodes to Markdown."""
        if isinstance(node, NavigableString):
            self.markdown_lines.append(as_markdown(node))
            return

        logging.debug(f"SingleLineParser: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        if node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.markdown_lines.append("#" * int(node.name[1]) + " ")
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['p']:
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['strong']:
            # TODO(JK): Determine if <strong> should be respected in headings
            if node.parent.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                for child in node.children:
                    self.convert_recursively(child)
                return

            self.markdown_lines.append(" **")
            for child in node.children:
                self.convert_recursively(child)
            self.markdown_lines.append("** ")
        elif node.name in ['em']:
            self.markdown_lines.append(" *")
            for child in node.children:
                self.convert_recursively(child)
            self.markdown_lines.append("* ")
        elif node.name in ['code']:
            self.markdown_lines.append("`")
            for child in node.children:
                self.convert_recursively(child)
            self.markdown_lines.append("`")
        elif node.name in ['span']:
            # The `style` prop expects a mapping from style properties to values, not a string.
            # For example, style={{marginRight: spacing + 'em'}} when using JSX.
            # For now, I will not handle the style prop and <span>.
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['ac:structured-macro']:
            """
<ac:structured-macro ac:name="status" ac:schema-version="1" ac:macro-id="a935cf67-ed54-4b6b-aafd-63cbebe654e1">
    <ac:parameter ac:name="title">Step 1</ac:parameter>
    <ac:parameter ac:name="colour">Blue</ac:parameter>
</ac:structured-macro>
            """
            if node.get('name') == 'status':
                self.markdown_lines.append("**[")
                for child in node.children:
                    self.convert_recursively(child)
                self.markdown_lines.append("]**")
            else:
                # For other structured macros, we can just log or skip
                logging.warning(f"SingleLineParser: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
                for child in node.children:
                    self.convert_recursively(child)
            return
        elif node.name in ['ac:parameter']:
            if node.get('name') == 'title':
                for child in node.children:
                    self.convert_recursively(child)
                return
            elif node.get('name') == 'colour':
                # ac:parameter with colour is not needed in Markdown
                return
            else:
                logging.warning(f"SingleLineParser: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
                for child in node.children:
                    self.convert_recursively(child)
                return
        elif node.name in ['ac:inline-comment-marker']:
            # ac:inline-comment-marker is a Confluence-specific tag that can be bypassed
            for child in node.children:
                self.convert_recursively(child)
            return
        elif node.name in ['br']:
            # <br/> is a line break, we can replace it with a whitespace in single line context
            self.markdown_lines.append(" ")
            return
        elif node.name in ['a']:
            href = node.get('href', '#')
            self.markdown_lines.append("[")
            for child in node.children:
                self.markdown_lines.append(SingleLineParser(child).as_markdown)
            self.markdown_lines.append(f"]({href})")
            return
        elif node.name in ['ac:link']:
            """
            <ac:link>
                <ri:page ri:content-title="Slack DM - Workflow 알림 유형" ri:version-at-save="7"/>
                <ac:link-body>Slack DM 개인 알림 사용하기</ac:link-body>
            </ac:link>
            """
            link_body = '(ERROR: Link body not found)'
            href = '#'
            for child in node.children:
                if isinstance(child, Tag) and child.name == 'ac:link-body':
                    link_body = SingleLineParser(child).as_markdown
                if isinstance(child, Tag) and child.name == 'ri:page':
                    href = child.get('content-title', '#')
            self.markdown_lines.append(f'[{link_body}]({href})')
            return
        elif node.name in ['ac:link-body']:
            # ac:link-body is used in ac:link, we can process it as a regular text
            for child in node.children:
                self.convert_recursively(child)
            return
        elif node.name in ['li']:
            # Extract text from <p> only.
            for child in node.children:
                if isinstance(child, Tag) and child.name == 'p':
                    self.convert_recursively(child)
                elif isinstance(child, NavigableString):
                    logging.debug(f'Skip extracting text from NavigableString({repr(child)}) under <li>')
                else:
                    logging.debug(f'Skip extracting text from <{child.name}> under <li>')
            return
        else:
            logging.warning(f"SingleLineParser: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]')
            for child in node.children:
                self.convert_recursively(child)

        return

class MultiLineParser:
    def __init__(self, node):
        self.node = node
        self.list_stack = []
        self.markdown_lines = []

    @property
    def as_markdown(self):
        """Convert the node to Markdown format."""
        self.convert_recursively(self.node)
        # Return the markdown lines as a list of strings
        return self.markdown_lines

    def convert_recursively(self, node):
        """Recursively convert child nodes to Markdown."""
        if isinstance(node, NavigableString):
            # This is a leaf node with text
            text = (
                node.replace('\u00A0', ' ') # Replace NBSP with space
            )
            self.markdown_lines.append(text)
            return

        logging.debug(f"MultiLineParser: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        if node.name in ['ac:structured-macro', 'ac:rich-text-body', 'ac:adf-content']:
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['p']:
            for child in node.children:
                self.markdown_lines.append(SingleLineParser(child).as_markdown)
                self.markdown_lines.append(" ")  # Add a space after a child of paragraphs
            # Add an empty line after paragraphs
            self.markdown_lines.append('\n')
        elif node.name in ['ul', 'ol']:
            self.convert_ul_ol(node)
        elif node.name in ['ac:image']:
            self.convert_image(node)
        elif node.name in ['a']:
            self.markdown_lines.append(SingleLineParser(node).as_markdown)
        else:
            logging.warning(f"MultiLineParser: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]')
            self.markdown_lines.append('\n')
            for child in node.children:
                self.convert_recursively(child)
            self.markdown_lines.append('\n')

    def convert_ul_ol(self, node):
        self.list_stack.append(node.name)
        counter = 1
        for child in node.children:
            if child.name == 'li':
                self.convert_li(child, node.name, counter)
                counter += 1
            else:
                if isinstance(child, NavigableString):
                    logging.debug(f'Skip extracting text from NavigableString({repr(child)}) under <{node.name}>')
                else:
                    logging.warning(f'Skip extracting text from <{child.name}> under <li>')
        self.list_stack.pop()
        return

    def convert_li(self, node, list_type, counter=None):
        indent = " " * 4 * (len(self.list_stack) - 1)
        if list_type == 'ul':
            prefix = f"{indent}* "
        else:
            prefix = f"{indent}{counter}. "

        text = SingleLineParser(node).as_markdown
        self.markdown_lines.append(f'{prefix}{text}')
        self.markdown_lines.append('\n')

        # Handle nested lists
        for child in node.children:
            if child.name in ['ul', 'ol']:
                self.convert_ul_ol(child)
        return

    def convert_image(self, node):
        """
        Process Confluence-specific image tags (ac:image) and convert them to Markdown format.

        Example XHTML:
        <ac:image ac:align="center" ac:layout="center" ac:original-height="668" ac:original-width="1024"
                 ac:custom-width="true" ac:alt="image-20240806-095511.png" ac:width="760">
            <ri:attachment ri:filename="image-20240806-095511.png" ri:version-at-save="1"/>
            <ac:caption><p>How QueryPie Works</p></ac:caption>
            <ac:adf-mark key="border" size="1" color="#091e4224"/>
        </ac:image>

        Converts to Markdown:
        ![image-20240806-095511.png](image-20240806-095511.png)
        *How QueryPie Works*
        """
        logging.debug(f"Processing Confluence image: {node}")

        # Extract image attributes
        align = node.get('align', 'center')
        alt_text = node.get('alt', '')

        # Find the attachment filename
        image_filename = ''
        attachment = node.find('ri:attachment')
        if attachment:
            image_filename = attachment.get('filename', '')
            if not image_filename:
                # Log warning if filename is still empty
                logging.warning("'filename' attribute is empty, check XML namespace handling")
        else:
            logging.warning(f'No attachment found in <ac:image> from {ancestors(node)}, no filename to use.')

        # Find caption if present
        caption_text = ''
        caption = node.find('ac:caption')
        if caption:
            caption_paragraph = caption.find('p')
            if caption_paragraph:
                caption_text = SingleLineParser(caption_paragraph).as_markdown

        # Create markdown image with alt text and filename
        if not alt_text and image_filename:
            alt_text = image_filename

        # Add the image in markdown format
        self.markdown_lines.append(f'<p align="{align}">')
        self.markdown_lines.append('\n')
        # TODO(JK): Link will be resolved later
        #self.markdown_lines.append(f"![{alt_text}]({image_filename})")
        self.markdown_lines.append(f"<div>[{alt_text}]()</div>")
        self.markdown_lines.append('\n')

        # Add caption if present
        if caption_text:
            self.markdown_lines.append(f"*{caption_text}*")
            self.markdown_lines.append('\n')

        self.markdown_lines.append(f'</p>')
        self.markdown_lines.append('\n')

class ConfluenceToMarkdown:
    def __init__(self):
        self.in_table = False
        self.table_data = []
        self.current_row = []
        self.rowspan_tracker = {}
        self.colspan_tracker = {}
        self.current_table_row = 0
        self.is_header_row = False
        self.markdown_lines = []
        self.list_stack = []
        self.inside_code_block = False
        self.code_language = ""
        self._imports = {}

    @property
    def imports(self):
        markdown = []
        if 'Callout' in self._imports and self._imports['Callout']:
            markdown.append("import { Callout } from 'nextra/components'")
        if len(markdown) > 0:
            markdown.append("") # Add an empty line after imports
        return markdown

    def add_import(self, module_name, condition=True):
        """Add an import statement to the list of imports."""
        if condition:
            self._imports[module_name] = True
        else:
            self._imports[module_name] = False

    def convert(self, html_content):
        # Replace XML namespace prefixes
        html_content = re.sub(r'\sac:', ' ', html_content)
        html_content = re.sub(r'\sri:', ' ', html_content)
        
        # Remove special characters before parsing
        html_content = html_content.replace(ZWSP, '')
        html_content = html_content.replace(LRM, '')
        html_content = html_content.replace(HANGUL_FILLER, '')
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Start conversion
        self.process_node(soup)

        # Join all markdown lines and return
        return "\n".join(chain(self.imports, self.markdown_lines))

    def process_node(self, node):
        if isinstance(node, NavigableString):
            text = node.strip()
            if text and not self.inside_code_block:
                if self.in_table:
                    # Only add text to current cell if we're in a table
                    if self.current_row:
                        if isinstance(self.current_row[-1], str):
                            self.current_row[-1] += text
                        else:
                            self.current_row.append(text)
                else:
                    self.markdown_lines.append(text)
            elif self.inside_code_block:
                # For code blocks, preserve original text including whitespace
                self.markdown_lines.append(str(node))
            return

        tmp = node.get_text(strip=True).splitlines()
        logging.debug(f"ConfluenceToMarkdown: type={type(node).__name__}, name={node.name}, value={repr(tmp[0] if tmp else '')}")

        if node.name == '[document]':
            # Start processing from the body of the document
            for child in node.children:
                self.process_node(child)
            return
        if node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.markdown_lines.append(SingleLineParser(node).as_markdown)
        elif node.name == 'p':
            text = self.get_text(node)
            if text:
                self.markdown_lines.append(text)
                self.markdown_lines.append("")  # Add an empty line after paragraphs
        elif node.name == 'strong' or node.name == 'b':
            text = self.get_text(node)
            self.markdown_lines.append(f"**{text}**")
        elif node.name == 'em' or node.name == 'i':
            text = self.get_text(node)
            self.markdown_lines.append(f"*{text}*")
        elif node.name == 'a':
            href = node.get('href', '#')
            text = self.get_text(node)
            self.markdown_lines.append(f"[{text}]({href})")
        elif node.name in ['ul', 'ol']:
            self.markdown_lines.append(''.join(MultiLineParser(node).as_markdown))
        elif node.name == 'table':
            self.process_table(node)
        elif node.name in ['code', 'pre']:
            self.process_code(node)
        elif node.name == 'ac:structured-macro':
            self.handle_structured_macro(node)
        elif node.name == 'ac:adf-extension':
            self.handle_adf_extension(node)
        elif node.name == 'div' or node.name == 'span':
            # Process children of div/span elements
            for child in node.children:
                self.process_node(child)
        elif node.name == 'br':
            self.markdown_lines.append("\n")
        elif node.name == 'hr':
            self.markdown_lines.append("---")
            self.markdown_lines.append("")
        elif node.name == 'img':
            alt = node.get('alt', '')
            src = node.get('src', '')
            self.markdown_lines.append(f"![{alt}]({src})")
        elif node.name == 'tr' or node.name == 'td' or node.name == 'th':
            # These are handled in the process_table method
            pass
        elif node.name in ['ac:layout', 'ac:layout-section', 'ac:layout-cell']:
            # Skip layout tags, as they are not needed in Markdown
            for child in node.children:
                self.process_node(child)
        elif node.name == 'body' or node.name == 'html' or node.name == None:
            # Just process children
            for child in node.children:
                self.process_node(child)
        elif node.name == 'ac:image':
            self.markdown_lines.append(''.join(MultiLineParser(node).as_markdown))
        else:
            logging.warning(f"Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            # Default behavior for other tags: process children
            for child in node.children:
                self.process_node(child)
    
    def get_text(self, node):
        if isinstance(node, NavigableString):
            text = str(node)
            # Remove NBSP at the beginning and end of the text
            return self.trim_nbsp(text)
        
        if hasattr(node, 'get_text'):
            text = node.get_text()
            if node.name in ['p']:
                # Encode < and > to prevent conflict with JSX syntax.
                # Confluence xhtml does not allow JSX syntax in <p/>, so this is safe.
                if '<' in text or '>' in text:
                    text = self.encode_lt_gt(text)
                    logging.debug(f"encode_lt_gt node={node.name} text={text}")
            if node.name in ['li']:
                if '{' in text or '}' in text:
                    text = backtick_curly_braces(text)

            return self.trim_nbsp(text)
        
        text = ""
        for child in node.children:
            if isinstance(child, NavigableString):
                text += str(child)
            elif hasattr(child, 'get_text'):
                text += child.get_text()
        
        return self.trim_nbsp(text)

    def encode_lt_gt(self, text):
        """Encode < and > as &lt; and &gt;"""
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        return text

    def trim_nbsp(self, text):
        """Remove NBSP characters at the beginning and end of text."""
        # Replace NBSP characters with regular spaces
        text = text.replace('\u00A0', ' ')
        return text.strip()

    def process_table(self, table_node):
        self.in_table = True
        self.table_data = []
        self.current_table_row = 0
        self.rowspan_tracker = {}
        
        # Process all rows
        rows = table_node.find_all(['tr'])
        
        for row_idx, row in enumerate(rows):
            self.current_row = []
            cells = row.find_all(['th', 'td'])
            
            # Apply rowspan from previous rows
            col_idx = 0
            for tracked_col, (span_left, content) in sorted(self.rowspan_tracker.items()):
                if span_left > 0:
                    # Insert content from cells spanning from previous rows
                    self.current_row.append(content)
                    # Decrement the remaining rowspan
                    self.rowspan_tracker[tracked_col] = (span_left - 1, content)
                    col_idx += 1
            
            # Process current row cells
            for cell_idx, cell in enumerate(cells):
                colspan = int(cell.get('colspan', 1))
                rowspan = int(cell.get('rowspan', 1))
                
                cell_content = self.get_text(cell)
                
                # Add cell content to current row
                self.current_row.append(cell_content)
                
                # Handle colspan by adding empty cells
                for _ in range(1, colspan):
                    self.current_row.append("")
                
                # Track cells with rowspan > 1 for next rows
                if rowspan > 1:
                    self.rowspan_tracker[col_idx + cell_idx] = (rowspan - 1, cell_content)
            
            # Add the row to table data
            self.table_data.append(self.current_row)
            
            # Check if it's a header row (contains th elements)
            if row.find('th') and row_idx == 0:
                self.is_header_row = True
        
        # Convert table data to markdown
        markdown_table = self.table_data_to_markdown()
        self.markdown_lines.append(markdown_table)
        self.markdown_lines.append("")  # Add empty line after table
        self.in_table = False
    
    def table_data_to_markdown(self):
        if not self.table_data or not any(self.table_data):
            return ""
        
        # Determine the number of columns based on the row with the most cells
        num_cols = max(len(row) for row in self.table_data)
        
        # Ensure all rows have the same number of columns
        normalized_data = []
        for row in self.table_data:
            normalized_row = row + [""] * (num_cols - len(row))
            normalized_data.append(normalized_row)
        
        # Calculate the maximum width of each column
        col_widths = [0] * num_cols
        for row in normalized_data:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Build the markdown table
        md_table = []
        
        # Header row
        header_row = "| " + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(normalized_data[0])) + " |"
        md_table.append(header_row)
        
        # Separator row
        separator = "| " + " | ".join("-" * col_widths[i] for i in range(num_cols)) + " |"
        md_table.append(separator)
        
        # Data rows
        for row in normalized_data[1:]:
            data_row = "| " + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)) + " |"
            md_table.append(data_row)
        
        return "\n".join(md_table)
    
    def process_code(self, node):
        self.inside_code_block = True
        
        # Try to determine the language
        language = node.get('class', '')
        if language and isinstance(language, str) and language.startswith('language-'):
            language = language.split('-')[1]
        else:
            language = ""
        
        code_content = node.get_text()
        
        # Start the code block
        self.markdown_lines.append(f"```{language}")
        self.markdown_lines.append(code_content)
        self.markdown_lines.append("```")
        self.markdown_lines.append("")  # Add empty line after code block
        
        self.inside_code_block = False

    def handle_structured_macro(self, node):
        macro_name = node.get('name', '')
        if macro_name in ['tip', 'info', 'note', 'warning']:
            self.add_import('Callout')

            markdown = []
            # https://nextra.site/docs/built-ins/callout
            # Confluence has broken namings of panels.
            if macro_name == 'tip': # success
                markdown.append('<Callout type="default">')
            elif macro_name == 'info': # info
                markdown.append('<Callout type="info">')
            elif macro_name == 'note': # note
                markdown.append('<Callout type="important">')
            elif macro_name == 'warning': # error - a broken name
                markdown.append('<Callout type="error">')
            else:
                markdown.append('<Callout>')
                logging.warning(f"Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            markdown.append('\n')

            logging.debug(f'MultiLineParser(node).as_markdown={MultiLineParser(node).as_markdown}')
            markdown.extend(MultiLineParser(node).as_markdown)
            markdown.append('</Callout>')
            markdown.append('\n')
            self.markdown_lines.append(''.join(markdown))
        elif macro_name in ['panel']: # Custom panel
            self.add_import('Callout')

            parameter = node.find('ac:parameter', {'name': 'panelIconText'})
            rich_text_body = node.find('ac:rich-text-body')

            markdown = []
            # https://nextra.site/docs/built-ins/callout
            # Confluence has broken namings of panels.
            if parameter:
                markdown.append(f'<Callout type="info" emoji="{parameter.text}">')
            else:
                markdown.append('<Callout>')
                logging.warning(f'Cannot find <ac:parameter ac:name="panelIconText"> under <ac:structured-macro: ac:name="{macro_name}">')
            markdown.append('\n')

            if rich_text_body:
                markdown.extend(MultiLineParser(rich_text_body).as_markdown)
            else:
                logging.warning(f'Cannot find <ac:rich-text-body> under <ac:structured-macro: ac:name="{macro_name}">')

            markdown.append('</Callout>')
            markdown.append('\n')
            self.markdown_lines.append(''.join(markdown))
        elif macro_name in ['code']:
            self.process_code_macro(node)
        elif macro_name in ['toc']:
            # Table of contents macro, we can skip it, as toc is provided by the Markdown renderer by default
            logging.debug("Skipping TOC macro")
        else:
            # For other macros, we can just log or skip
            logging.warning(f"Unhandled macro: {macro_name}, processing children")
            for child in node.children:
                self.process_node(child)

    def handle_adf_extension(self, node):
        logging.debug(f'ac:adf-extension')
        for child in node.children:
            if not isinstance(child, Tag):
                continue

            node_type = child.get('type', '(unknown)')
            logging.debug(f'child of ac:adf-extension name={child.name} type={node_type}')
            if child.name == 'ac:adf-node' and node_type == 'panel':
                self.handle_adf_node_panel(child)
                return

    def handle_adf_node_panel(self, node):
        self.add_import('Callout')

        panel_type = 'unknown'
        adf_attribute = node.find('ac:adf-attribute', {'key': 'panel-type'})
        if adf_attribute:
            panel_type = adf_attribute.text
            logging.debug(f'Found <ac:adf-attribute key="panel-type"> text={adf_attribute.text}')
        else:
            logging.warning(f"No <ac:adf-attribute> in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")

        adf_content = node.find('ac:adf-content')
        if adf_content:
            logging.debug(f'Found <ac:adf-content> text={adf_content.text}')
        else:
            logging.warning(f"No <ac:adf-content> in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")

        markdown = []
        if panel_type == 'note':
            markdown.append('<Callout type="important">')
        else:
            markdown.append('<Callout>')
            logging.warning(f'Unexpected panel-type of "{panel_type}" in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}')
        markdown.append('\n')

        if adf_content:
            markdown.extend(MultiLineParser(adf_content).as_markdown)

        markdown.append('</Callout>')
        markdown.append('\n')
        self.markdown_lines.append(''.join(markdown))


    def process_code_macro(self, macro_node):
        self.inside_code_block = True
        
        # Find language parameter and code content
        language = ""
        cdata = "TODO(JK): Handle code macro content extraction"
        
        # Look for language parameter
        language_param = macro_node.find('parameter', {'name': 'language'})
        if language_param:
            language = language_param.get_text()
        
        # Look for code content in CDATA section
        plain_text_body = macro_node.find('ac:plain-text-body')
        if plain_text_body:
            # Extract CDATA content
            for item in plain_text_body.contents:
                if isinstance(item, CData):
                    cdata = str(item) # Convert CData object to string
                    break

        # Write the code block
        self.markdown_lines.append(f"```{language}")
        self.markdown_lines.append(cdata)
        self.markdown_lines.append("```")
        self.markdown_lines.append("")  # Add empty line after code block
        
        self.inside_code_block = False
        

def main():
    parser = argparse.ArgumentParser(description='Convert Confluence XHTML to Markdown')
    parser.add_argument('input_file', help='Input XHTML file path')
    parser.add_argument('output_file', help='Output Markdown file path')
    parser.add_argument('--log-level', 
                        choices=['debug', 'info', 'warning', 'error', 'critical'],
                        default='info',
                        help='Set the logging level (default: info)')
    args = parser.parse_args()
    
    # Configure logging with the specified level
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(level=log_level, format='%(levelname)s - %(funcName)s:%(lineno)d - %(message)s')

    # Store input file path in global variable
    global INPUT_FILE_PATH
    # Extract the last directory and filename from the path
    path = os.path.normpath(args.input_file)  # Normalize path for cross-platform compatibility
    dirname, filename = os.path.split(path)  # Split into directory and filename
    
    if dirname:
        # Get the last directory name
        last_dir = os.path.basename(dirname)
        # Combine last directory and filename
        INPUT_FILE_PATH = os.path.join(last_dir, filename)
    else:
        # If there's no directory part, just use the filename
        INPUT_FILE_PATH = filename

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        converter = ConfluenceToMarkdown()
        markdown_content = converter.convert(html_content)
        
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logging.info(f"Successfully converted {args.input_file} to {args.output_file}")
    
    except Exception as e:
        import traceback
        tb = traceback.extract_tb(e.__traceback__)
        if tb:
            last_frame = tb[-1]
            file_name = last_frame.filename.split('/')[-1]
            line_no = last_frame.lineno
            func_name = last_frame.name
            code = last_frame.line
            logging.error(f"Error during conversion: {e} (in {file_name}, function '{func_name}', line {line_no}, code: '{code}')")
        else:
            logging.error(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()