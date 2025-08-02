#!/usr/bin/env python3
"""
Confluence XHTML to Markdown Converter

This script converts Confluence XHTML export to clean Markdown,
handling special cases like:
- CDATA sections in code blocks
- Tables with colspan and rowspan attributes
- Structured macros and other Confluence-specific elements
"""

import argparse
import logging
import os
import re
import sys
from itertools import chain

from bs4 import BeautifulSoup, Tag, NavigableString
from bs4.element import CData

# Global variable to store an input file path
INPUT_FILE_PATH = ""

# Hidden characters constants
ZWSP = '\u200b'  # Zero Width Space
LRM = '\u200e'  # Left-to-Right Mark
HANGUL_FILLER = '\u3164'  # Hangul Filler

LANGUAGE = 'en'


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
    pattern = r'(\{\{?[\w\s\-\_\.\|\:\u2026]{1,60}\}\}?)'
    return re.sub(pattern, r'`\1`', text)


def as_markdown(node):
    if isinstance(node, NavigableString):
        # This is a leaf node with text
        text = (
            node.replace('\u00A0', ' ')  # Replace NBSP with space
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


def get_html_attributes(node):
    """Extract HTML attributes from a node and format them as a string."""
    if not hasattr(node, 'attrs') or not node.attrs:
        return ""

    attrs_list = []
    for attr_name, attr_value in node.attrs.items():
        # TODO(JK): Do not include style attribute of Tag for now.
        # Or, npm run build fails.
        # MDX requires style property in JSX format, style={{ name: value, ...}}.
        if attr_name == 'style':
            continue

        if isinstance(attr_value, list):
            # Convert list-type attribute values (e.g., class) to a space-separated string
            attr_value = ' '.join(attr_value)
        elif isinstance(attr_value, bool):
            # For boolean attributes, include only the attribute name when the value is True
            if attr_value:
                attrs_list.append(attr_name)
            continue

        # Escape values of HTML attributes
        attr_value = attr_value.replace('"', '&quot;')
        attrs_list.append(f'{attr_name}="{attr_value}"')

    if attrs_list:
        return " " + " ".join(attrs_list)
    return ""


class SingleLineParser:
    def __init__(self, node):
        self.node = node
        self.markdown_lines = []
        self.applicable_nodes = {
            'span',
            'strong', 'em', 'code', 'u',
            'br', 'a',
            'ac:inline-comment-marker',
            'ac:emoticon',
            'time',
        }
        self.unapplicable_nodes = {
            'ul', 'ol', 'li',
            'ac:plain-text-body',
        }
        self._debug_markdown = False

    @property
    def as_markdown(self):
        """Convert the node to Markdown format."""
        self.convert_recursively(self.node)
        # Join all lines without a space and remove leading/trailing whitespace
        # It is supposed to preserve whitespace in the middle of the text
        return "".join(self.markdown_lines)

    @property
    def applicable(self):

        def _is_applicable_recursively(node):
            if isinstance(node, NavigableString):
                return True
            elif node.name in self.applicable_nodes:
                for child in node.children:
                    if _is_applicable_recursively(child):
                        pass
                    else:
                        return False
                return True
            elif node.name in ['ac:link', 'ac:image']:
                return True
            elif node.name in ['ac:structured-macro']:
                attr_name = node.get('name', '')
                if attr_name in ['status']:
                    return True
                else:
                    return False
            else:
                return False

        return _is_applicable_recursively(self.node)

    def convert_recursively(self, node):
        """Recursively convert child nodes to Markdown."""
        if isinstance(node, NavigableString):
            text = as_markdown(node)
            if node.parent.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                self.markdown_lines.append(text.strip())
            else:
                self.markdown_lines.append(as_markdown(node))
            return

        logging.debug(f"SingleLineParser: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        if self._debug_markdown:
            self.markdown_lines.append(f'<{node.name}>')
        if node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.markdown_lines.append("#" * int(node.name[1]) + " ")
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['p', 'th', 'td']:
            for child in node.children:
                # DEBUG(JK): Uncomment below lines for debugging
                # self.markdown_lines.append(f"({child.name if child.name else 'NavigableString'})")
                self.convert_recursively(child)
                # self.markdown_lines.append(f"(/{child.name if child.name else 'NavigableString'})")
        elif node.name in ['strong']:
            # CORRECTION: <strong> is ignored in headings
            if node.parent.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                for child in node.children:
                    self.convert_recursively(child)
            else:
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
        elif node.name in ['u']:
            if node.parent.name != 'a':  # CORRECTION: Use plain style in anchor text.
                self.markdown_lines.append("<u>")
            for child in node.children:
                self.convert_recursively(child)
            if node.parent.name != 'a':
                self.markdown_lines.append("</u>")
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
        elif node.name in ['ac:parameter']:
            if node.get('name') == 'title':
                for child in node.children:
                    self.convert_recursively(child)
            elif node.get('name') == 'colour':
                # ac:parameter with colour is not needed in Markdown
                pass
            else:
                logging.warning(f"SingleLineParser: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
                for child in node.children:
                    self.convert_recursively(child)
        elif node.name in ['ac:inline-comment-marker']:
            # ac:inline-comment-marker is a Confluence-specific tag that can be bypassed
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['br']:
            # <br/> is a line break. Just keep using <br/>.
            self.markdown_lines.append("<br/>")
        elif node.name in ['a']:
            href = node.get('href', '#')
            self.markdown_lines.append("[")
            for child in node.children:
                self.markdown_lines.append(SingleLineParser(child).as_markdown)
            self.markdown_lines.append(f"]({href})")
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
        elif node.name in ['ac:link-body']:
            # ac:link-body is used in ac:link, we can process it as a regular text
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['li']:
            # Extract text from <p> only.
            for child in node.children:
                if isinstance(child, Tag) and child.name == 'p':
                    self.convert_recursively(child)
                elif isinstance(child, NavigableString):
                    logging.debug(f'Skip extracting text from NavigableString({repr(child)}) under <li>')
                else:
                    logging.debug(f'Skip extracting text from <{child.name}> under <li>')
        elif node.name in ['ac:emoticon']:
            """
            <ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:"
                         ac:emoji-id="atlassian-check_mark" ac:emoji-fallback=":check_mark:"/>
            """
            shortname = node.get('emoji-shortname')
            if shortname:
                self.markdown_lines.append(f'{shortname}')
        elif node.name in ['time']:
            """
            <time datetime="2025-07-02">
            """
            datetime_attr = node.get('datetime', '')
            if datetime_attr:
                try:
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))

                    if LANGUAGE == 'ko':
                        # Korean: YYYY년 MM월 DD일
                        formatted_date = date_obj.strftime('%Y년 %m월 %d일')
                    elif LANGUAGE == 'ja':
                        # Japanese: YYYY年MM月DD日
                        formatted_date = date_obj.strftime('%Y年%m月%d日')
                    elif LANGUAGE == 'en':
                        # English: Jan 1, 2025
                        formatted_date = date_obj.strftime('%b %d, %Y')
                    else:
                        # Default: ISO format
                        formatted_date = date_obj.strftime('%Y-%m-%d')

                    self.markdown_lines.append(formatted_date)
                except ValueError:
                    # Use original text if date parsing fails
                    logging.warning(
                        f"Failed to parse datetime '{datetime_attr}' in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            else:
                # Process child nodes if the datetime attribute is not present
                logging.warning(f"Failed to get datetime attribute in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
        elif node.name in ['ac:image']:
            self.convert_inline_image(node)
        else:
            logging.warning(f"SingleLineParser: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]')
            for child in node.children:
                self.convert_recursively(child)

        if self._debug_markdown:
            self.markdown_lines.append(f'</{node.name}>')
        return

    def convert_inline_image(self, node):
        """
        Process Confluence-specific image tags <ac:image> and convert them to Markdown format.

        Example XHTML:
        <ac:image ac:align="center" ac:layout="center" ac:original-height="668" ac:original-width="1024"
                 ac:custom-width="true" ac:alt="image-20240806-095511.png" ac:width="760">
            <ri:attachment ri:filename="image-20240806-095511.png" ri:version-at-save="1"/>
            <ac:caption><p>How QueryPie Works</p></ac:caption>
            <ac:adf-mark key="border" size="1" color="#091e4224"/>
        </ac:image>

        Converts to Markdown:
            ![image-20240806-095511.png](image-20240806-095511.png)
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
                # Log warning if the filename is still empty
                logging.warning("'filename' attribute is empty, check XML namespace handling")
        else:
            logging.warning(f'No attachment found in <ac:image> from {ancestors(node)}, no filename to use.')

        # Create a Markdown image with alt text and filename
        if not alt_text and image_filename:
            alt_text = image_filename

        # Add the image in Markdown format
        # self.markdown_lines.append(f"![{alt_text}]({image_filename})")
        self.markdown_lines.append(f"![{alt_text}]()")  # TODO(JK): Fix image link


class MultiLineParser:
    def __init__(self, node):
        self.node = node
        self.list_stack = []
        self.markdown_lines = []
        self._debug_markdown = False

    @property
    def as_markdown(self):
        """Convert the node to Markdown format."""
        self.convert_recursively(self.node)
        # Return the Markdown lines as a list of strings
        return self.markdown_lines

    def convert_recursively(self, node):
        """Recursively convert child nodes to Markdown."""
        if isinstance(node, NavigableString):
            logging.warning(f"MultiLineParser: Unexpected NavigableString, text={repr(node.text)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            # Do not append unexpected NavigableString to markdown_lines.
            return

        logging.debug(f"MultiLineParser: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        attr_name = node.get('name', '(none)')
        if node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Headings can exist in a <Callout> block.
            self.markdown_lines.append(SingleLineParser(node).as_markdown)
            self.markdown_lines.append('\n')
        elif node.name in ['ac:structured-macro'] and attr_name in ['tip', 'info', 'note', 'warning']:
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['ac:structured-macro'] and attr_name in ['code']:
            self.convert_structured_macro_code(node)
        elif node.name in ['ac:structured-macro'] and attr_name in ['expand']:
            self.convert_structured_macro_expand(node)
        elif node.name in [
            'ac:rich-text-body',  # Child of <ac:structured-macro name="panel">
            'ac:adf-content',  # Child of <ac:adf-extension>
        ]:
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['p']:
            for child in node.children:
                if isinstance(child, NavigableString):
                    self.markdown_lines.append(SingleLineParser(child).as_markdown)
                elif SingleLineParser(child).applicable:
                    self.markdown_lines.append(SingleLineParser(child).as_markdown)
                else:
                    if self._debug_markdown:
                        self.markdown_lines.append(f'<{child.name}>')
                    self.markdown_lines.extend(MultiLineParser(child).as_markdown)
                    if self._debug_markdown:
                        self.markdown_lines.append(f'</{child.name}>')
            self.markdown_lines.append('\n')
            # Add an empty line after paragraphs
            # self.markdown_lines.append('\n')
        elif node.name in ['br']:
            # <br/> is a line break. Just keep using <br/>.
            # Append '\n' for <br/> in MultiLineParser.
            self.markdown_lines.append("<br/>\n")
        elif node.name in ['ul', 'ol']:
            self.convert_ul_ol(node)
        elif node.name in ['ac:image']:
            self.convert_image(node)
        elif node.name in ['a']:
            self.markdown_lines.append(SingleLineParser(node).as_markdown)
        elif node.name in ['hr']:
            self.markdown_lines.append(f'---\n')
        elif node.name in ['blockquote']:
            markdown = []
            for child in node.children:
                markdown.extend(MultiLineParser(child).as_markdown)
            lines = ''.join(markdown).splitlines()
            for to_quote in lines:
                self.markdown_lines.append(f'> {to_quote}')
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
        Process Confluence-specific image tags <ac:image> and convert them to Markdown format.

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
                # Log warning if the filename is still empty
                logging.warning("'filename' attribute is empty, check XML namespace handling")
        else:
            logging.warning(f'No attachment found in <ac:image> from {ancestors(node)}, no filename to use.')

        # Find a caption if present
        caption_text = ''
        caption = node.find('ac:caption')
        if caption:
            caption_paragraph = caption.find('p')
            if caption_paragraph:
                caption_text = SingleLineParser(caption_paragraph).as_markdown

        # Create a Markdown image with alt text and filename
        if not alt_text and image_filename:
            alt_text = image_filename

        # Add the image in Markdown format
        self.markdown_lines.append(f'<p align="{align}">')
        self.markdown_lines.append('\n')
        # TODO(JK): Link will be resolved later
        # self.markdown_lines.append(f"![{alt_text}]({image_filename})")
        self.markdown_lines.append(f"<div>[{alt_text}]()</div>")
        self.markdown_lines.append('\n')

        # Add caption if present
        if caption_text:
            self.markdown_lines.append(f"*{caption_text}*")
            self.markdown_lines.append('\n')

        self.markdown_lines.append(f'</p>')
        self.markdown_lines.append('\n')

    def convert_structured_macro_code(self, node):
        # Find language parameter and code content
        language = ""
        cdata = "TODO(JK): Handle code macro content extraction"

        # Look for language parameter
        language_param = node.find('ac:parameter', {'name': 'language'})
        if language_param:
            language = language_param.get_text()

        # Look for code content in the CDATA section
        plain_text_body = node.find('ac:plain-text-body')
        if plain_text_body:
            # Extract CDATA content
            for item in plain_text_body.contents:
                if isinstance(item, CData):
                    cdata = str(item)  # Convert CData object to string
                    break

        # Write the code block
        self.markdown_lines.append(f"```{language}")
        self.markdown_lines.append("\n")
        self.markdown_lines.append(cdata)
        self.markdown_lines.append("\n")
        self.markdown_lines.append("```")
        self.markdown_lines.append("\n")

    def convert_structured_macro_expand(self, node):
        """
        <ac:structured-macro ac:name="expand" ac:schema-version="1" ac:macro-id="1df48224-102c-464b-931c-e5e53abcb781">
            <ac:parameter ac:name="title">generate_kubepie_sa.sh 스크립트 컨텐츠</ac:parameter>
            <ac:rich-text-body>
            blah... blah...
            </ac:rich-text-body>
        </ac:structured-macro><ul>
        """
        self.markdown_lines.append(f"<details>\n")
        # Find title parameter
        title = "(Untitled)"
        title_param = node.find('ac:parameter', {'name': 'title'})
        if title_param:
            title = title_param.get_text()
        self.markdown_lines.append(f'<summary>{title}</summary>\n')

        # Look for code content in the CDATA section
        rich_text_body = node.find('ac:rich-text-body')
        if rich_text_body:
            self.markdown_lines.extend(MultiLineParser(rich_text_body).as_markdown)

        self.markdown_lines.append(f"</details>\n")


class TableToNativeMarkdown:
    def __init__(self, node):
        self.node = node
        self.markdown_lines = []
        self.applicable_nodes = {
            'table', 'tbody', 'col', 'tr', 'colgroup', 'th', 'td',
            'p', 'strong', 'em', 'span', 'code', 'br', 'a',
            'ac:inline-comment-marker',
            'ac:emoticon',
            'ac:link', 'ac:link-body', 'ri:page',
            'ac:image', 'ri:attachment',
        }
        self.unapplicable_nodes = {
            'ul', 'ol', 'li',
            'ac:structured-macro', 'ac:parameter', 'ac:plain-text-body',
        }

    @property
    def as_markdown(self):
        """Convert the node to Markdown format."""
        self.convert_recursively(self.node)
        # Return the Markdown lines as a list of strings
        return self.markdown_lines

    @property
    def applicable(self):
        # Get all child nodes that are not NavigableString (including nested children)
        descendants = set()

        def collect_node_names(node):
            for child in node.children:
                if not isinstance(child, NavigableString):
                    descendants.add(child.name)
                    # Recursively collect names from children of children
                    collect_node_names(child)

        collect_node_names(self.node)
        unapplicable_descendants = descendants.difference(self.applicable_nodes)
        if_applicable = descendants.issubset(self.applicable_nodes)
        if descendants.isdisjoint(self.unapplicable_nodes) and if_applicable:
            logging.info(f"TableToNativeMarkdown: Applicable {print_node_with_properties(self.node)} has {descendants}")
        elif unapplicable_descendants.issubset(self.unapplicable_nodes):
            logging.info(f"TableToNativeMarkdown: Unapplicable {print_node_with_properties(self.node)} has {descendants}")
            logging.info(f"TableToNativeMarkdown: Unapplicable due to {unapplicable_descendants} that is a subset of self.unapplicable_nodes")
        else:
            unexpected = unapplicable_descendants.difference(self.unapplicable_nodes)
            logging.warning(f"TableToNativeMarkdown: Unapplicable {print_node_with_properties(self.node)} has {descendants}")
            logging.warning(f"TableToNativeMarkdown: Unapplicable due to {unapplicable_descendants} that has unexpected descendants: {unexpected}")

        return if_applicable

    def convert_recursively(self, node):
        """Recursively convert child nodes to Markdown."""
        if isinstance(node, NavigableString):
            logging.warning(f"TableToNativeMarkdown: Unexpected NavigableString from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(node.text)
            return

        logging.debug(f"TableToNativeMarkdown: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        if node.name in ['table']:
            self.convert_table(node)
        else:
            logging.warning(f"TableToNativeMarkdown: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]')
            self.markdown_lines.append('\n')
            for child in node.children:
                self.convert_recursively(child)
            self.markdown_lines.append('\n')

    def convert_table(self, node):
        table_data = []
        rowspan_tracker = {}

        # Process all rows
        rows = node.find_all(['tr'])

        for row_idx, row in enumerate(rows):
            current_row = []
            cells = row.find_all(['th', 'td'])

            # Apply rowspan from previous rows
            col_idx = 0
            for tracked_col, (span_left, content) in sorted(rowspan_tracker.items()):
                if span_left > 0:
                    # Insert content from cells spanning from previous rows
                    current_row.append(content)
                    # Decrement the remaining rowspan
                    rowspan_tracker[tracked_col] = (span_left - 1, content)
                    col_idx += 1

            # Process current row cells
            for cell_idx, cell in enumerate(cells):
                colspan = int(cell.get('colspan', 1))
                rowspan = int(cell.get('rowspan', 1))

                cell_content = SingleLineParser(cell).as_markdown

                # Add cell content to the current row
                current_row.append(cell_content)

                # Handle colspan by adding empty cells
                for _ in range(1, colspan):
                    current_row.append("")

                # Track cells with rowspan > 1 for next rows
                if rowspan > 1:
                    rowspan_tracker[col_idx + cell_idx] = (rowspan - 1, cell_content)

            # Add the row to table data
            table_data.append(current_row)

            # Check if it's a header row
            if row.find('th') and row_idx == 0:
                is_header_row = True

        # Convert table data to Markdown
        markdown_table = self.table_data_to_markdown(table_data)
        self.markdown_lines.extend(markdown_table)

    def table_data_to_markdown(self, table_data):
        if not table_data or not any(table_data):
            return ""

        # Determine the number of columns based on the row with the most cells
        num_cols = max(len(row) for row in table_data)

        # Ensure all rows have the same number of columns
        normalized_data = []
        for row in table_data:
            normalized_row = row + [""] * (num_cols - len(row))
            normalized_data.append(normalized_row)

        # Calculate the maximum width of each column
        col_widths = [0] * num_cols
        for row in normalized_data:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Build the Markdown table
        md_table = []

        # Header row
        header_row = "| " + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(normalized_data[0])) + " |"
        md_table.append(header_row)
        md_table.append("\n")

        # Separator row
        separator = "| " + " | ".join("-" * col_widths[i] for i in range(num_cols)) + " |"
        md_table.append(separator)
        md_table.append("\n")

        # Data rows
        for row in normalized_data[1:]:
            data_row = "| " + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)) + " |"
            md_table.append(data_row)
            md_table.append("\n")

        return ''.join(md_table)


class TableToHtmlTable:
    def __init__(self, node):
        self.node = node
        self.markdown_lines = []

    @property
    def as_markdown(self):
        """Convert the node to Markdown format."""
        self.convert_recursively(self.node)
        # Return Markdown lines as a list of strings
        return self.markdown_lines

    def convert_recursively(self, node):
        """Recursively convert child nodes to Markdown."""
        if isinstance(node, NavigableString):
            logging.warning(f"TableToHtmlTable: Unexpected NavigableString from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(node.text)
            return

        logging.debug(f"TableToHtmlTable: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")

        if node.name in ['table', 'thead', 'tbody', 'tfoot', 'tr', 'colgroup']:
            """Convert table node to HTML table markup."""
            attrs = get_html_attributes(node)
            self.markdown_lines.append(f"<{node.name}{attrs}>")
            self.markdown_lines.append('\n')

            for child in node.children:
                if not isinstance(child, NavigableString):
                    self.convert_recursively(child)

            self.markdown_lines.append(f"</{node.name}>")
            self.markdown_lines.append('\n')
        elif node.name in ['th', 'td']:
            attrs = get_html_attributes(node)
            self.markdown_lines.append(f"<{node.name}{attrs}>")
            self.markdown_lines.append('\n')

            for child in node.children:
                if not isinstance(child, NavigableString):
                    td = ''.join(MultiLineParser(child).as_markdown)
                    self.markdown_lines.append(td)

            self.markdown_lines.append(f"</{node.name}>")
            self.markdown_lines.append('\n')
        elif node.name == 'col':
            """Convert col node to HTML col markup."""
            attrs = get_html_attributes(node)
            self.markdown_lines.append(f"<col{attrs}/>")
            self.markdown_lines.append('\n')
        else:
            logging.warning(f"TableToHtmlTable: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]')
            self.markdown_lines.append('\n')
            for child in node.children:
                self.convert_recursively(child)
            self.markdown_lines.append('\n')


class StructuredMacroToCallout:
    def __init__(self, node):
        self.node = node
        self.markdown_lines = []

    @property
    def as_markdown(self):
        """Convert the node to Markdown format."""
        self.convert_recursively(self.node)
        # Return the Markdown lines as a list of strings
        return self.markdown_lines

    @property
    def applicable(self):
        attr_name = self.node.get('name', '')
        if self.node.name in ['ac:structured-macro']:
            if attr_name in ['tip', 'info', 'note', 'warning']:
                return True
            elif attr_name in ['panel']:
                return True
        return False

    @property
    def has_applicable_nodes(self):

        def _has_applicable_node(node):
            if isinstance(node, NavigableString):
                return False
            elif StructuredMacroToCallout(node).applicable:
                return True
            else:
                for child in node.children:
                    if _has_applicable_node(child):
                        return True
            return False

        return _has_applicable_node(self.node)

    def convert_recursively(self, node):
        """Recursively convert child nodes to Markdown."""
        if isinstance(node, NavigableString):
            logging.warning(f"StructuredMacroToCallout: Unexpected NavigableString from {ancestors(node)} in {INPUT_FILE_PATH}")
            # Do not append unexpected NavigableString to markdown_lines.
            return

        logging.debug(f"StructuredMacroToCallout: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        attr_name = node.get('name', '')
        if node.name in ['ac:structured-macro'] and attr_name in ['tip', 'info', 'note', 'warning']:
            # https://nextra.site/docs/built-ins/callout
            # Confluence has broken namings of panels.
            if attr_name == 'tip':  # success
                self.markdown_lines.append('<Callout type="default">')
            elif attr_name == 'info':  # info
                self.markdown_lines.append('<Callout type="info">')
            elif attr_name == 'note':  # note
                self.markdown_lines.append('<Callout type="important">')
            elif attr_name == 'warning':  # error - a broken name
                self.markdown_lines.append('<Callout type="error">')
            else:
                self.markdown_lines.append(f'<Callout> {"{"}/* <ac:structured-macro ac:name="{attr_name}"> */{"}"}')
                logging.warning(f"Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append('\n')

            for child in node.children:
                self.markdown_lines.extend(MultiLineParser(child).as_markdown)

            self.markdown_lines.append('</Callout>')
            self.markdown_lines.append('\n')
        elif node.name in ['ac:structured-macro'] and attr_name in ['panel']:
            parameter = node.find('ac:parameter', {'name': 'panelIconText'})
            rich_text_body = node.find('ac:rich-text-body')
            # https://nextra.site/docs/built-ins/callout
            # Confluence has broken namings of panels.
            if parameter:
                self.markdown_lines.append(f'<Callout type="info" emoji="{parameter.text}">')
            else:
                self.markdown_lines.append('<Callout>')
                logging.warning(
                    f'Cannot find <ac:parameter ac:name="panelIconText"> under {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}')
            self.markdown_lines.append('\n')

            if rich_text_body:
                self.markdown_lines.extend(MultiLineParser(rich_text_body).as_markdown)
            else:
                logging.warning(
                    f'Cannot find <ac:rich-text-body> under {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}')

            self.markdown_lines.append('</Callout>')
            self.markdown_lines.append('\n')
        else:
            logging.warning(f"StructuredMacroToCallout: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]')
            self.markdown_lines.append('\n')
            for child in node.children:
                self.convert_recursively(child)
            self.markdown_lines.append('\n')


class AdfExtensionToCallout:
    def __init__(self, node):
        self.node = node
        self.markdown_lines = []

    @property
    def as_markdown(self):
        """Convert the node to Markdown format."""
        self.convert_recursively(self.node)
        # Return the Markdown lines as a list of strings
        return self.markdown_lines

    @property
    def applicable(self):
        if not self.node.name in ['ac:adf-extension']:
            return False

        for child in self.node.children:
            if not isinstance(child, Tag):
                continue
            node_type = child.get('type', '(unknown)')
            logging.debug(f'child of ac:adf-extension name={child.name} type={node_type}')
            if child.name == 'ac:adf-node' and node_type == 'panel':
                return True
        return False

    @property
    def has_applicable_nodes(self):

        def _has_applicable_node(node):
            if isinstance(node, NavigableString):
                return False
            elif AdfExtensionToCallout(node).applicable:
                return True
            else:
                for child in node.children:
                    if _has_applicable_node(child):
                        return True
            return False

        return _has_applicable_node(self.node)

    def convert_recursively(self, node):
        """Recursively convert child nodes to Markdown."""
        if isinstance(node, NavigableString):
            logging.warning(f"AdfExtensionToCallout: Unexpected NavigableString from {ancestors(node)} in {INPUT_FILE_PATH}")
            # Do not append unexpected NavigableString to markdown_lines.
            return

        logging.debug(f"AdfExtensionToCallout: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        attr_key = node.get('type', '(unknown)')
        if node.name in ['ac:adf-extension']:
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['ac:adf-node'] and attr_key == 'panel':
            panel_type = 'unknown'
            adf_attribute = node.find('ac:adf-attribute', {'key': 'panel-type'})
            if adf_attribute:
                panel_type = adf_attribute.text
                logging.debug(f'Found <ac:adf-attribute key="panel-type"> text={adf_attribute.text}')
            else:
                logging.warning(f"No <ac:adf-attribute> in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")

            if panel_type == 'note':
                self.markdown_lines.append('<Callout type="important">')
            else:
                self.markdown_lines.append('<Callout>')
                logging.warning(
                    f'Unexpected panel-type of "{panel_type}" in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}')
            self.markdown_lines.append('\n')

            adf_content = node.find('ac:adf-content')
            if adf_content:
                self.markdown_lines.extend(MultiLineParser(adf_content).as_markdown)
            else:
                logging.warning(f"No <ac:adf-content> in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")

            self.markdown_lines.append('</Callout>')
            self.markdown_lines.append('\n')
        elif node.name in ['ac:adf-fallback']:
            pass  # Ignore <ac:adf-fallback>
        else:
            logging.warning(f"AdfExtensionToCallout: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]')
            self.markdown_lines.append('\n')
            for child in node.children:
                self.convert_recursively(child)
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
        self._debug_markdown = False

    @property
    def imports(self):
        markdown = []
        if 'Callout' in self._imports and self._imports['Callout']:
            markdown.append("import { Callout } from 'nextra/components'")
        if len(markdown) > 0:
            markdown.append("")  # Add an empty line after imports
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

        if StructuredMacroToCallout(soup).has_applicable_nodes:
            self.add_import('Callout')
        elif AdfExtensionToCallout(soup).has_applicable_nodes:
            self.add_import('Callout')

        # Start conversion
        self.process_node(soup)

        # Join all Markdown lines and return
        return "\n".join(chain(self.imports, self.markdown_lines))

    def process_node(self, node):
        if isinstance(node, NavigableString):
            if self._debug_markdown:
                self.markdown_lines.append(f"TODO(JK): ConfluenceToMarkdown: Unexpected NavigableString of from {ancestors(node)} in {INPUT_FILE_PATH}")
            text = node.strip()
            if text and not self.inside_code_block:
                if self.in_table:
                    # Only add text to the current cell if we're in a table
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

        if node.name in [
            '[document]',  # Start processing from the body of the document
            'html', 'body',
            'ac:layout', 'ac:layout-section', 'ac:layout-cell',  # Skip layout tags
        ]:
            for child in node.children:
                self.process_node(child)
        elif node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.markdown_lines.append(SingleLineParser(node).as_markdown)
        elif node.name == 'p':
            paragraph = ''.join(MultiLineParser(node).as_markdown)
            paragraph = paragraph.strip() + '\n'  # TODO(JK): Improve this hacking.
            self.markdown_lines.append(paragraph)
        elif node.name in ['ul', 'ol']:
            self.markdown_lines.append(''.join(MultiLineParser(node).as_markdown))
        elif node.name in ['blockquote']:
            self.markdown_lines.append(''.join(MultiLineParser(node).as_markdown))
        elif node.name == 'table':
            native_markdown = TableToNativeMarkdown(node)
            if native_markdown.applicable:
                self.markdown_lines.append(''.join(native_markdown.as_markdown))
            else:
                logging.info(f'ConfluenceToMarkdown: use TableToHtmlTable(node) in {INPUT_FILE_PATH}')
                self.markdown_lines.append(''.join(TableToHtmlTable(node).as_markdown))
        elif node.name == 'ac:structured-macro':
            attr_name = node.get('name', '')
            if StructuredMacroToCallout(node).applicable:
                self.markdown_lines.append(''.join(StructuredMacroToCallout(node).as_markdown))
            elif attr_name in ['code', 'expand']:
                self.markdown_lines.append(''.join(MultiLineParser(node).as_markdown))
            elif attr_name in ['toc']:
                # Table of contents macro, we can skip it, as toc is provided by the Markdown renderer by default
                logging.debug("Skipping TOC macro")
            elif attr_name in ['children']:
                self.markdown_lines.append(f'(Unsupported xhtml node: &lt;ac:structured-macro name="children"&gt;)')
                pass
            else:
                if self._debug_markdown:
                    self.markdown_lines.append(f'{print_node_with_properties(node)}')
                # For other macros, we can just log or skip
                logging.warning(f"Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
                for child in node.children:
                    self.process_node(child)
        elif node.name == 'ac:adf-extension':
            if AdfExtensionToCallout(node).applicable:
                self.markdown_lines.append(''.join(AdfExtensionToCallout(node).as_markdown))
            else:
                self.markdown_lines.append(''.join(MultiLineParser(node).as_markdown))
        elif node.name == 'div' or node.name == 'span':
            self.markdown_lines.append(''.join(MultiLineParser(node).as_markdown))
        elif node.name == 'hr':
            self.markdown_lines.append(''.join(MultiLineParser(node).as_markdown))
        elif node.name == 'ac:image':  # In-Use as 2025-08-01
            self.markdown_lines.append(''.join(MultiLineParser(node).as_markdown))
        else:
            logging.warning(f"Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            # Default behavior for other tags: process children
            for child in node.children:
                self.process_node(child)


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

    # Store the input file path in a global variable
    global INPUT_FILE_PATH, LANGUAGE

    # Extract language code from the output file path
    output_path = os.path.normpath(args.output_file)
    path_parts = output_path.split(os.sep)

    # Look for 2-letter language code in the path
    detected_language = 'en'  # Default to English
    for part in path_parts:
        if len(part) == 2 and part.isalpha():
            # Check if it's a known language code
            if part in ['ko', 'ja', 'en']:
                detected_language = part
                break

    # Update global LANGUAGE variable
    LANGUAGE = detected_language
    logging.info(f"Detected language from output path: {LANGUAGE}")

    # Extract the last directory and filename from the path
    path = os.path.normpath(args.input_file)  # Normalize path for cross-platform compatibility
    dirname, filename = os.path.split(path)  # Split into directory and filename

    if dirname:
        # Get the last directory name
        last_dir = os.path.basename(dirname)
        # Combine the last directory and filename
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
