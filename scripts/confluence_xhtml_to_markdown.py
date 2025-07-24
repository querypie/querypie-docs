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
import html
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import argparse
from bs4 import BeautifulSoup, Tag, NavigableString
from bs4.element import CData
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
            # This is a leaf node with text
            text = (
                node.replace('\u00A0', ' ') # Replace NBSP with space
            )
            self.markdown_lines.append(text)
            return

        logging.debug(f"SingleLineParser: node={type(node)}, name={node.name}, text={node.get_text()}")
        if node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.markdown_lines.append("#" * int(node.name[1]) + " ")
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['strong']:
            # TODO(JK): Determine if <strong> should be respected in headings
            if node.parent.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                for child in node.children:
                    self.convert_recursively(child)
                return

            self.markdown_lines.append("**")
            for child in node.children:
                self.convert_recursively(child)
            self.markdown_lines.append("**")
        elif node.name in ['code']:
            self.markdown_lines.append("`")
            for child in node.children:
                self.convert_recursively(child)
            self.markdown_lines.append("`")
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
                logging.warning(f"SingleLineParser: Unexpected ac:structured-macro: {node.get('ac:name')}, processing children")
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
                logging.warning(f"SingleLineParser: Unexpected ac:parameter ac:name={node.get('ac:name')}")
                for child in node.children:
                    self.convert_recursively(child)
                return
        elif node.name in ['ac:inline-comment-marker']:
            # ac:inline-comment-marker is a Confluence-specific tag that can be bypassed
            for child in node.children:
                self.convert_recursively(child)
            return
        elif node.name in ['br']:
            # <br/> should be ignored in single line context
            return
        else:
            logging.warning(f"SingleLineParser: Unexpected node={node.name}")
            self.markdown_lines.append(f"[{node.name}]")
            for child in node.children:
                self.convert_recursively(child)

        return

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
        
    def convert(self, html_content):
        # Replace XML namespace prefixes
        html_content = re.sub(r'\sac:', ' ', html_content)
        html_content = re.sub(r'\sri:', ' ', html_content)
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Start conversion
        self.process_node(soup)

        # Join all markdown lines and return
        return "\n".join(self.markdown_lines)

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

        logging.debug(f"ConfluenceToMarkdown:process_node() node.name={node.name}, text={node.get_text()}")
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
        elif node.name == 'ul':
            self.list_stack.append('ul')
            for child in node.children:
                if child.name == 'li':
                    self.process_list_item(child, 'ul')
            self.list_stack.pop()
            self.markdown_lines.append("")  # Add empty line after list
        elif node.name == 'ol':
            self.list_stack.append('ol')
            counter = 1
            for child in node.children:
                if child.name == 'li':
                    self.process_list_item(child, 'ol', counter)
                    counter += 1
            self.list_stack.pop()
            self.markdown_lines.append("")  # Add empty line after list
        elif node.name == 'table':
            self.process_table(node)
        elif node.name in ['code', 'pre']:
            self.process_code(node)
        elif node.name == 'ac:structured-macro':
            self.handle_structured_macro(node)
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
        elif node.name == 'body' or node.name == 'html' or node.name == None:
            # Just process children
            for child in node.children:
                self.process_node(child)
        elif node.name == 'ac:image':
            self.process_image(node)
        else:
            logging.warning(f"ConfluenceToMarkdown: Unexpected node={node.name}, processing children")
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
                    text = self.quote_embraced_text(text)
                    logging.debug(f"quote_embraced_text node={node.name} text={text}")

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

    def quote_embraced_text(self, text):
        """Quote text that is embraced by curly braces.
        
        If there are 20 or fewer word characters (including spaces, Korean characters, 
        alphabets, etc.) between the curly braces, format as `{ ...}`.
        """
        # Use regex to find all occurrences of text within curly braces
        # that contain 20 or fewer word characters
        # \u2026 is the ellipsis character, `...` which is often used in Confluence
        pattern = r'(\{\{?[\w\s\-\|\u2026]{1,60}\}\}?)'
        if not re.search(pattern, text):
            return text

        # Replace all matching patterns with backtick-quoted version
        result = re.sub(pattern, r'`\1`', text)
        logging.debug(f"Quoted embraced text: {result} in original text: {text}")
        return result

    def trim_nbsp(self, text):
        """Remove NBSP characters at the beginning and end of text."""
        # Replace NBSP characters with regular spaces
        text = text.replace('\u00A0', ' ')
        return text.strip()
    
    def process_list_item(self, node, list_type, counter=None):
        indent = "  " * (len(self.list_stack) - 1)
        if list_type == 'ul':
            prefix = f"{indent}* "
        else:
            prefix = f"{indent}{counter}. "
        
        text = self.get_text(node)
        self.markdown_lines.append(f"{prefix}{text}")
        
        # Handle nested lists
        for child in node.children:
            if child.name == 'ul' or child.name == 'ol':
                self.list_stack.append(child.name)
                new_counter = 1
                for subchild in child.children:
                    if subchild.name == 'li':
                        self.process_list_item(subchild, child.name, new_counter)
                        if child.name == 'ol':
                            new_counter += 1
                self.list_stack.pop()
    
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

    def handle_structured_macro(self, macro_node):
        # Handle structured macros like 'info', 'note', etc.
        macro_name = macro_node.get('name', '')
        if macro_name in ['info', 'note', 'tip', 'warning', 'caution']:
            # TODO(JK): Handle these macros with specific formatting
            for child in macro_node.children:
                self.process_node(child)
        elif macro_name in ['code']:
            self.process_code_macro(macro_node)
        elif macro_name in ['toc']:
            # Table of contents macro, we can skip it, as toc is provided by the Markdown renderer by default
            logging.debug("Skipping TOC macro")
        else:
            # For other macros, we can just log or skip
            logging.warning(f"Unhandled macro: {macro_name}, processing children")
            for child in macro_node.children:
                self.process_node(child)

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
        
    def process_image(self, image_node):
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
        logging.debug(f"Processing Confluence image: {image_node}")
        
        # Extract image attributes
        align = image_node.get('align', 'center')
        alt_text = image_node.get('alt', '')
        
        # Find the attachment filename
        attachment = image_node.find('ri:attachment')
        image_filename = ''
        if attachment:
            image_filename = attachment.get('filename', '')
            if not image_filename:
                # Log warning if filename is still empty
                logging.warning("'filename' attribute is empty, check XML namespace handling")
        else:
            logging.warning("No attachment found in ac:image, no filename to use.")
        
        # Find caption if present
        caption_text = ''
        caption = image_node.find('ac:caption')
        if caption:
            caption_p = caption.find('p')
            if caption_p:
                caption_text = self.get_text(caption_p)
        
        # Create markdown image with alt text and filename
        if not alt_text and image_filename:
            alt_text = image_filename
            
        # Add the image in markdown format
        self.markdown_lines.append(f'<p align="{align}">')
        #self.markdown_lines.append(f"[{alt_text}]({image_filename})")
        self.markdown_lines.append(f"<div>[{alt_text}]()</div>") # TODO(JK): Link will be resolved later

        # Add caption if present
        if caption_text:
            self.markdown_lines.append(f"*{caption_text}*")
        self.markdown_lines.append(f'</p>')
        # Add empty line after image
        self.markdown_lines.append("")

def main():
    parser = argparse.ArgumentParser(description='Convert Confluence XHTML to Markdown')
    parser.add_argument('input_file', help='Input XHTML file path')
    parser.add_argument('output_file', help='Output Markdown file path')
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        converter = ConfluenceToMarkdown()
        markdown_content = converter.convert(html_content)
        
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logging.info(f"Successfully converted {args.input_file} to {args.output_file}")
    
    except Exception as e:
        logging.error(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()