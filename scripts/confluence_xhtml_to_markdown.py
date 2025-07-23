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
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            
        if node.name == 'h1':
            self.markdown_lines.append(f"# {self.get_text(node)}")
        elif node.name == 'h2':
            self.markdown_lines.append(f"## {self.get_text(node)}")
        elif node.name == 'h3':
            self.markdown_lines.append(f"### {self.get_text(node)}")
        elif node.name == 'h4':
            self.markdown_lines.append(f"#### {self.get_text(node)}")
        elif node.name == 'h5':
            self.markdown_lines.append(f"##### {self.get_text(node)}")
        elif node.name == 'h6':
            self.markdown_lines.append(f"###### {self.get_text(node)}")
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
        elif node.name == 'code' or node.name == 'pre':
            self.process_code(node)
        elif node.name == 'structured-macro' and node.get('name') == 'code':
            self.process_code_macro(node)
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
        else:
            # Default behavior for other tags: process children
            for child in node.children:
                self.process_node(child)
    
    def get_text(self, node):
        if isinstance(node, NavigableString):
            return str(node)
        
        if hasattr(node, 'get_text'):
            return node.get_text()
        
        text = ""
        for child in node.children:
            if isinstance(child, NavigableString):
                text += str(child)
            elif hasattr(child, 'get_text'):
                text += child.get_text()
        
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
    
    def process_code_macro(self, macro_node):
        self.inside_code_block = True
        
        # Find language parameter and code content
        language = ""
        code_content = ""
        
        # Look for language parameter
        language_param = macro_node.find('parameter', {'name': 'language'})
        if language_param:
            language = language_param.get_text()
        
        # Look for code content in CDATA section
        plain_text_body = macro_node.find('plain-text-body')
        if plain_text_body:
            # Extract CDATA content
            cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', str(plain_text_body), re.DOTALL)
            if cdata_match:
                code_content = cdata_match.group(1)
        
        # Write the code block
        self.markdown_lines.append(f"```{language}")
        self.markdown_lines.append(code_content)
        self.markdown_lines.append("```")
        self.markdown_lines.append("")  # Add empty line after code block
        
        self.inside_code_block = False

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