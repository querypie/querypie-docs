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
import filecmp
import logging
import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Optional, Dict, List, Any, TypedDict
from urllib.parse import unquote, urlparse

import yaml
from bs4 import BeautifulSoup, Tag, NavigableString
from bs4.element import CData

from text_utils import clean_text

try:
    import emoji
    EMOJI_AVAILABLE = True
except ImportError:
    EMOJI_AVAILABLE = False


# Type definitions for page_v1 structure
class PageV1(TypedDict, total=False):
    """Type definition for page_v1 data structure"""
    id: str
    type: str
    ari: str
    base64EncodedAri: str
    status: str
    title: str
    ancestors: List[Dict[str, Any]]
    macroRenderedOutput: Dict[str, Any]
    body: Dict[str, Any]
    extensions: Dict[str, Any]
    _expandable: Dict[str, Any]
    _links: Dict[str, str]


# Type definitions for pages dictionary structure
class PageInfo(TypedDict, total=False):
    """Type definition for page information in pages.yaml"""
    page_id: str
    title: str
    breadcrumbs: List[str]
    breadcrumbs_en: List[str]
    path: List[str]


class Attachment:
    """
    <ri:attachment filename="image-20240725-070857.png" version-at-save="1">
    <ri:attachment filename="스크린샷 2024-08-01 오후 2.50.06.png" version-at-save="1">
    """

    def __init__(self, node: Tag, input_dir: str, output_dir: str, public_dir: str) -> None:
        filename = node.get('filename', '')
        if not filename:
            logging.warning(f"add_attachment: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            return

        # Apply unicodedata.normalize to prevent unmatched string comparison.
        # Use Normalization Form Canonical Composition for the unicode normalization.
        filename = unicodedata.normalize('NFC', filename)
        self.original: str = filename
        self.filename: str = normalize_screenshots(filename)
        self.used: bool = False

        self.input_dir: str = input_dir
        self.output_dir: str = output_dir
        self.public_dir: str = public_dir
        logging.debug(f"Attachment: filename={filename} input_dir={self.input_dir} output_dir={self.output_dir} public_dir={self.public_dir}")

    def __str__(self) -> str:
        return f'{"{"}filename="{self.filename}",original="{self.original}"{"}"}'

    def copy_to_destination(self) -> None:
        source_file = clean_text(os.path.join(self.input_dir, self.original))
        if os.path.exists(source_file):
            logging.debug(f"Source file found: {repr(source_file)}")
        else:
            logging.warning(f"Source file not found: {repr(source_file)}")
            return

        logging.debug(f"public_dir={self.public_dir} output_dir={self.output_dir}")
        destination_dir = os.path.normpath(os.path.join(self.public_dir, './' + self.output_dir))
        logging.debug(f"Destination directory: {destination_dir}")
        if not os.path.exists(destination_dir):
            logging.debug(f"Destination directory not found: {repr(destination_dir)}")
            os.makedirs(destination_dir)
        destination_file = os.path.join(destination_dir, self.filename)
        if os.path.exists(destination_file):
            # compare source_file and destination_file are equivalent.
            if filecmp.cmp(source_file, destination_file):
                logging.debug(f"Destination file already exists: {repr(destination_file)}")
                os.utime(destination_file, None)
            else:
                logging.warning(f"Destination file already exists but different: {repr(destination_file)}")
        else:
            shutil.copyfile(source_file, destination_file)
            # Change file permission to 0644
            os.chmod(destination_file, 0o644)

    def as_markdown(self, caption: Optional[str] = None, width: Optional[str] = None, align: str = None) -> str:
        if not caption:
            caption = self.filename

        image_extensions = ('.png', '.gif', '.jpg', '.jpeg', '.webp', '.svg')
        if self.filename.lower().endswith(image_extensions):
            safe_caption = caption.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
            attrs = [f'src="{self.output_dir}/{self.filename}"', f'alt="{safe_caption}"']
            if width:
                attrs.append(f'width="{width}"')
            return f'<img {" ".join(attrs)} />'
        else:
            return f'[{caption}]({self.output_dir}/{self.filename})'


# Type alias for pages dictionary
PagesDict = Dict[str, PageInfo]

# Global variable to store an input file path
INPUT_FILE_PATH = ""
OUTPUT_FILE_PATH = ""
LANGUAGE = 'en'

# Global variables to store data
PAGES_BY_TITLE: PagesDict = {}
PAGES_BY_ID: PagesDict = {}
GLOBAL_PAGE_V1: Optional[PageV1] = None
GLOBAL_ATTACHMENTS: List[Attachment] = []
GLOBAL_LINK_MAPPING: Dict[str, str] = {}  # Mapping of link text -> pageId from page.v1.yaml

# Confluence status macro color to Badge component color mapping
CONFLUENCE_COLOR_TO_BADGE_COLOR = {
    'Green': 'green',
    'Blue': 'blue',
    'Red': 'red',
    'Yellow': 'yellow',
    'Grey': 'grey',
    'Gray': 'grey',
    'Purple': 'purple',
}

def confluence_url():
    if GLOBAL_PAGE_V1:
        page_id = GLOBAL_PAGE_V1.get('id')
        return f'https://querypie.atlassian.net/wiki/spaces/QM/pages/{page_id}/'
    else:
        return 'https://querypie.atlassian.net/wiki/spaces/QM/overview'


def parse_confluence_url(href: str) -> Optional[Dict[str, str]]:
    """
    Parse a Confluence URL and extract page_id and anchor fragment.

    Args:
        href: The URL to parse (e.g., https://querypie.atlassian.net/wiki/spaces/QM/pages/1454342158/Identity+Providers#anchor)

    Returns:
        Dictionary with 'page_id' and 'anchor' keys, or None if not a Confluence URL
    """
    if not href:
        return None

    # Check if it's a Confluence URL
    if 'atlassian.net/wiki/spaces/' not in href:
        return None

    parsed = urlparse(href)
    path = parsed.path
    fragment = parsed.fragment  # The anchor part after #

    # Extract page_id from path: /wiki/spaces/QM/pages/{page_id}/...
    match = re.search(r'/pages/(\d+)/', path)
    if not match:
        return None

    page_id = match.group(1)

    return {
        'page_id': page_id,
        'anchor': fragment if fragment else ''
    }


def convert_confluence_url(href: str) -> tuple[str, Optional[str]]:
    """
    Convert a Confluence URL to an internal markdown link.

    Args:
        href: The URL to convert

    Returns:
        tuple: (converted_href, readable_link_text)
               readable_link_text is provided when the original link text (URL) should be replaced
               Format:
               - Same page segment: "#섹션 제목"
               - Different page segment: "문서 제목#섹션 제목" or "Unknown Title#섹션 제목"
               - Different page (no segment): "문서 제목" or "Unknown Title"
    """
    parsed = parse_confluence_url(href)
    if not parsed:
        return href, None

    current_page_id = GLOBAL_PAGE_V1.get('id', '') if GLOBAL_PAGE_V1 else ''
    target_page_id = parsed['page_id']
    anchor = parsed['anchor']

    if target_page_id == current_page_id and anchor:
        # Same page segment link - convert to internal anchor
        decoded_anchor = unquote(anchor).lower()
        section_title = unquote(anchor).replace('-', ' ')
        readable_text = f'#{section_title}'
        logging.debug(f"Converted same-page segment link to #{decoded_anchor}")
        return f'#{decoded_anchor}', readable_text

    if anchor:
        # Different page with anchor
        target_page = PAGES_BY_ID.get(target_page_id)
        decoded_anchor = unquote(anchor).lower()
        section_title = unquote(anchor).replace('-', ' ')
        if target_page:
            target_path = relative_path_to_titled_page(target_page.get('title', ''))
            doc_title = target_page.get('title', 'Unknown Title')
            readable_text = f'{doc_title}#{section_title}'
            return f'{target_path}#{decoded_anchor}', readable_text
        logging.warning(f"Target page {target_page_id} not found in pages dictionary")
        readable_text = f'Unknown Title#{section_title}'
        return href, readable_text

    # Different page without anchor
    target_page = PAGES_BY_ID.get(target_page_id)
    if target_page:
        return relative_path_to_titled_page(target_page.get('title', '')), target_page.get('title')
    logging.warning(f"Target page {target_page_id} not found in pages dictionary")
    return href, 'Unknown Title'


def load_pages_yaml(yaml_path: str, pages_by_title: PagesDict, pages_by_id: PagesDict):
    """
    Load the pages.yaml file and populate the provided dictionaries with page information
    
    Args:
        yaml_path: Path to the pages.yaml file
        pages_by_title: Dictionary to be populated with title as key and page info as value
        pages_by_id: Dictionary to be populated with page_id as key and page info as value

    Returns:
        PagesDict: Dictionary with title as key and page info as value, or empty dict if file doesn't exist
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_string = f.read()
            yaml_data = yaml.safe_load(yaml_string)

            # Convert a list to dictionary with title as a key
            pages_dict: PagesDict = {}
            if isinstance(yaml_data, list):
                for page in yaml_data:
                    if not isinstance(page, dict):
                        logging.warning(f"Page info must be of type dict: {repr(page)}")
                        continue

                    title_orig = page.get('title_orig')
                    if not title_orig:
                        logging.warning(f"Page info must have a title_orig: {repr(page)}")
                        continue

                    if title_orig in pages_by_title:
                        logging.warning(f"title_orig ${repr(title_orig)} already exists in pages_by_title: {repr(pages_by_title[title_orig])}")
                        logging.warning(f"title_orig ${repr(title_orig)} is from {repr(page)}")
                        continue

                    pages_by_title[title_orig] = page
                    pages_by_id[page['page_id']] = page

            logging.info(f"Successfully loaded pages.yaml from {yaml_path} with {len(pages_by_id)} pages")
            return pages_dict
    except FileNotFoundError:
        logging.warning(f"Pages YAML file not found: {yaml_path}")
        return {}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {yaml_path}: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error loading pages.yaml from {yaml_path}: {e}")
        return {}


def get_page_v1() -> Optional[PageV1]:
    """Get the current page_v1 data"""
    global GLOBAL_PAGE_V1
    return GLOBAL_PAGE_V1


def get_attachments() -> List[Attachment]:
    """Get the current attachments list"""
    global GLOBAL_ATTACHMENTS
    return GLOBAL_ATTACHMENTS


def set_page_v1(page_v1: Optional[PageV1]) -> None:
    """Set the current page_v1 data"""
    global GLOBAL_PAGE_V1
    GLOBAL_PAGE_V1 = page_v1


def set_attachments(attachments: List[Attachment]) -> None:
    """Set the current attachments list"""
    global GLOBAL_ATTACHMENTS
    GLOBAL_ATTACHMENTS = attachments


def calculate_relative_path(current_path: List[str], target_path: List[str]):
    """
    Calculate a relative path from the current path to a target path using os.path.relpath
    
    Args:
        current_path (list): List of path components for the current page
        target_path (list): List of path components for the target page
        
    Returns:
        str: Relative path string
    """
    import os

    # Convert path lists to string paths
    current_path_str = os.path.join("/", *current_path) if current_path else ""
    target_path_str = os.path.join("/", *target_path) if target_path else ""
    current_base_dir = os.path.dirname(current_path_str)
    relative_path = os.path.relpath(target_path_str, current_base_dir)

    logging.debug(f"calculate_relative_path: current_path={current_path_str}, target_path={target_path_str}, relative_path={relative_path}")
    return relative_path


def relative_path_to_titled_page(title: str):
    if get_page_v1():
        this_title = get_page_v1().get('title')
        this_page = PAGES_BY_TITLE.get(this_title)
    else:
        this_page = None
        logging.warning(f"Page v1 not found in {INPUT_FILE_PATH}")

    if title:
        target_page = PAGES_BY_TITLE.get(title)
    else:
        target_page = None

    if this_page and target_page:
        relative_path = calculate_relative_path(this_page.get('path'), target_page.get('path'))
        if relative_path:
            href = relative_path
        else:
            href = "#invalid-relative-path"
    elif not target_page:
        logging.warning(f"Target title '{title}' not found in pages dictionary")
        href = "#target-title-not-found"
    else:
        logging.warning(f"Unexpected failure of relative_path_to_titled_page: {title}")
        href = "#unexpected-failure"
    return href


def load_page_v1_yaml(yaml_path: str) -> Optional[PageV1]:
    """
    Load page.v1.yaml file and return as a dictionary object
    
    Args:
        yaml_path (str): Path to the page.v1.yaml file
        
    Returns:
        PageV1: YAML content as PageV1 dictionary, or None if the file doesn't exist or has errors
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_string = f.read()
            yaml_data = yaml.safe_load(yaml_string)
            logging.info(f"Successfully loaded page.v1.yaml from {yaml_path}")
            return yaml_data
    except FileNotFoundError:
        logging.warning(f"Page v1 YAML file not found: {yaml_path}")
        return None
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {yaml_path}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error loading page.v1.yaml from {yaml_path}: {e}")
        return None


def build_link_mapping(page_v1: Optional[PageV1]) -> Dict[str, str]:
    """
    Build a mapping of link text -> pageId from page.v1.yaml body.view HTML

    This function parses the rendered HTML in page.v1.yaml's body.view section
    to extract links with their pageIds. This allows us to generate accurate
    Confluence URLs for external links (links to pages outside the current conversion scope).

    Args:
        page_v1 (Optional[PageV1]): The page.v1.yaml data structure

    Returns:
        Dict[str, str]: Mapping of link text to pageId
    """
    link_map = {}

    if not page_v1:
        logging.warning("No page.v1 data available to build link mapping")
        return link_map

    try:
        view_html = page_v1.get('body', {}).get('view', {}).get('value', '')

        if not view_html:
            logging.warning("No body.view HTML found in page.v1.yaml")
            return link_map

        soup = BeautifulSoup(view_html, 'html.parser')

        # Find all links with data-linked-resource-id attribute
        for link in soup.find_all('a', {'data-linked-resource-id': True}):
            text = link.get_text()
            page_id = link.get('data-linked-resource-id', '')
            resource_type = link.get('data-linked-resource-type', '')

            if text and page_id and resource_type == 'page':
                link_map[text] = page_id
                logging.debug(f"Link mapping: '{text}' -> pageId {page_id}")

        logging.info(f"Built link mapping with {len(link_map)} entries")

    except Exception as e:
        logging.error(f"Error building link mapping from page.v1.yaml: {e}")

    return link_map


def resolve_external_link(link_text: str, space_key: str, target_title: str) -> str:
    """
    Resolve external Confluence link URL using pageId from global link mapping

    This function attempts to generate an accurate Confluence URL for external links
    (links to pages outside the current conversion scope) by looking up the pageId
    from GLOBAL_LINK_MAPPING. If pageId is not found, it falls back to space overview
    or error link.

    Args:
        link_text (str): The link body text to match in GLOBAL_LINK_MAPPING
        space_key (str): The Confluence space key
        target_title (str): The target page title (for logging purposes)

    Returns:
        str: The resolved URL in one of these formats:
            - With pageId: https://querypie.atlassian.net/wiki/spaces/{space_key}/pages/{page_id}
            - Without pageId but with space_key: https://querypie.atlassian.net/wiki/spaces/{space_key}/overview
            - Without space_key: #link-error
    """
    page_id = GLOBAL_LINK_MAPPING.get(link_text)

    if page_id and space_key:
        # Generate accurate URL with pageId
        href = f'https://querypie.atlassian.net/wiki/spaces/{space_key}/pages/{page_id}'
        logging.info(f"Generated external Confluence link with pageId for '{link_text}' (title: '{target_title}'): {href}")
        return href
    elif space_key:
        # Fallback to space overview URL if no pageId found
        href = f'https://querypie.atlassian.net/wiki/spaces/{space_key}/overview'
        logging.warning(f"No pageId found for '{link_text}', using space overview for '{target_title}' in space '{space_key}': {href}")
        return href
    else:
        # No space key - show simple error message
        href = '#link-error'
        logging.warning(f"No space key found for external link to '{target_title}', using error anchor: {href}")
        return href


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


def navigable_string_as_markdown(node):
    if isinstance(node, NavigableString):
        # This is a leaf node with text
        text = clean_text(node.text)
        text = text.replace('\n', ' ')  # Replace newlines with space
        # Normalize multiple spaces to a single space
        text = re.sub(r'\s+', ' ', text)
        if node.parent.name == 'code':
            # Do not encode < and > or backtick_curly_braces if the parent node is `<code>`,
            # as it is backticked already and characters will be displayed correctly.
            pass
        else:
            # Encode < and > to prevent conflict with JSX syntax.
            text = text.replace('<', '&lt;').replace('>', '&gt;')
            text = backtick_curly_braces(text)
        return text
    else:
        # Fatal error and crash
        raise TypeError(f"as_markdown() expects a NavigableString, got: {type(node).__name__}")


def split_into_sentences(line):
    """
    Split a string into sentences using sentence-ending punctuation marks.
    
    Sentences are split at patterns matching (. ! ?) followed by whitespace.
    The punctuation marks are included in the preceding sentence.
    
    Args:
        line (str): The input string to split.
        
    Returns:
        list[str]: A list of sentences. If the string is empty or None,
                   returns an empty list. If no sentence terminators are found,
                   returns a list containing the original string.
    """
    if not line or not isinstance(line, str):
        return []
    
    # Pattern matches sentence-ending punctuation (. ! ?) followed by whitespace
    # Only matches when preceded by 3 non-digit characters
    #   - This condition prevents splitting on `1. Blah Blah... 2. Answer`.
    #   - This condition prevents splitting on `Q. Question... A. Answer`.
    # Using positive lookbehind to ensure 3 non-digit characters before punctuation
    # Using capturing group to preserve the punctuation in the split result
    pattern = r'(?<=\D{3})([.!?])\s+'

    # Split the string and preserve punctuation marks
    parts = re.split(pattern, line)
    
    # Reconstruct sentences: parts[0] is first sentence, parts[1] is punctuation,
    # parts[2] is next sentence, parts[3] is punctuation, etc.
    sentences = []
    current_sentence = ''
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Even indices are sentence parts
            current_sentence += part
        else:
            # Odd indices are punctuation marks
            current_sentence += part
            # Add the completed sentence (with punctuation) to the list
            if current_sentence.strip():
                sentences.append(current_sentence.strip())
            current_sentence = ''
    
    # Add the last sentence if there's any remaining text
    if current_sentence.strip():
        sentences.append(current_sentence.strip())
    
    # If no sentences were found (no sentence terminators), return the original string
    if not sentences:
        return [line.strip()] if line.strip() else []
    
    return sentences

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
        # TODO(JK): Do not include class attribute of Tag for now.
        # class="numberingColumn" might be the cause of broken table rendering.
        if attr_name in ['style', 'class']:
            continue
        
        # Remove local-id attribute (Confluence-specific, not needed in MDX)
        if attr_name == 'local-id':
            continue
        
        # Remove all data-* attributes (Confluence-specific metadata, not needed in MDX)
        if attr_name.startswith('data-'):
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


def datetime_ko_format(date_string):
    """
    Convert '2024-08-01 오후 2.50.06' format to '20240801-145006' format

    Args:
        date_string (str): Date/time string to convert

    Returns:
        str: Converted date/time string
    """
    try:
        # Split the input string into date and time parts
        # '2024-08-01 오후 2.50.06' -> ['2024-08-01', '오후 2.50.06']
        parts = date_string.split(' ')

        if len(parts) != 3:
            raise ValueError(f"Invalid date format: <{date_string}>")

        date_part = parts[0]  # '2024-08-01'
        ampm_part = parts[1]  # '오후'
        time_part = parts[2]  # '2.50.06'

        # Parse date part (YYYY-MM-DD -> YYYYMMDD)
        date_obj = datetime.strptime(date_part, '%Y-%m-%d')
        date_formatted = date_obj.strftime('%Y%m%d')

        # Parse time part
        time_parts = time_part.split('.')
        if len(time_parts) != 3:
            raise ValueError("Invalid time format.")

        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2])

        # Add 12 for PM (AM remains the same)
        if ampm_part == '오후' and hour != 12:
            hour += 12
        elif ampm_part == '오전' and hour == 12:
            hour = 0

        # Format time as HHMMSS
        time_formatted = f"{hour:02d}{minute:02d}{second:02d}"

        # Return a final result
        return f"{date_formatted}-{time_formatted}"

    except Exception as e:
        return f"Error: {str(e)}"


def normalize_screenshots(filename):
    screenshot_ko = unicodedata.normalize('NFC', '스크린샷')
    assert len(screenshot_ko) == 4  # Normalized string should have four characters.

    normalized = clean_text(filename)
    if re.match(rf'{screenshot_ko} \d\d\d\d-\d\d-\d\d .*.png', normalized):
        datetime_ko = normalized.replace(f'{screenshot_ko} ', '').replace('.png', '')
        datetime_std = datetime_ko_format(datetime_ko)
        normalized = 'screenshot-' + datetime_std + '.png'
    if normalized.find(' ') >= 0:
        normalized = normalized.replace(' ', '-')

    return normalized


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
            'ac:adf-fragment-mark', 'ac:adf-fragment-mark-detail',
        }
        self.unapplicable_nodes = {
            'ul', 'ol', 'li',
            'ac:plain-text-body',
        }
        self._debug_tags = {
            # 'a', 'ac:link', 'ri:page', 'ac:link-body',
        }

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
            elif node.name in ['ac:link', 'ac:image', 'ac:adf-fragment-mark']:
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
            text = navigable_string_as_markdown(node)
            if node.parent.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                self.markdown_lines.append(text.strip())
            else:
                self.markdown_lines.append(text)
            return

        logging.debug(f"SingleLineParser: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        if node.name in self._debug_tags:
            self.markdown_lines.append(f'{print_node_with_properties(node)}')

        if node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Adjust heading level: h1 -> h2, h2 -> h3, etc.
            # h6 remains h6 (max level)
            original_level = int(node.name[1])
            adjusted_level = min(original_level + 1, 6)
            self.markdown_lines.append("#" * adjusted_level + " ")
            self.markdown_lines.append(self.markdown_of_children(node))
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
                self.markdown_lines.append(self.markdown_of_children(node).strip())
                self.markdown_lines.append("** ")
        elif node.name in ['em']:
            self.markdown_lines.append(" *")
            self.markdown_lines.append(self.markdown_of_children(node).strip())
            self.markdown_lines.append("* ")
        elif node.name in ['code']:
            self.markdown_lines.append("`")
            self.markdown_lines.append(self.markdown_of_children(node).strip())
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

            Converts to:
            <Badge color="blue">Step 1</Badge>

            Note: Badge is registered as a global MDX component in src/mdx-components.js,
            so no import statement is needed in the generated MDX files.
            """
            if node.get('name') == 'status':
                title = ''
                color = 'grey'  # default color
                for child in node.children:
                    if isinstance(child, Tag) and child.name == 'ac:parameter':
                        if child.get('name') == 'title':
                            title = SingleLineParser(child).markdown_of_children(child)
                        elif child.get('name') == 'colour':
                            confluence_color = child.text.strip()
                            color = CONFLUENCE_COLOR_TO_BADGE_COLOR.get(confluence_color, 'grey')
                self.markdown_lines.append(f'<Badge color="{color}">{title}</Badge>')
            else:
                # For other structured macros, we can just log or skip
                logging.warning(f"SingleLineParser: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
                for child in node.children:
                    self.convert_recursively(child)
        elif node.name in ['ac:parameter']:
            # ac:parameter nodes are now handled within their parent ac:structured-macro
            # This block should only be reached if ac:parameter appears in unexpected contexts
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
            href, readable_anchor_text = convert_confluence_url(node.get('href', '#'))
            link_text = ''.join(SingleLineParser(child).as_markdown for child in node.children)
            if readable_anchor_text and link_text.startswith('http'):
                link_text = readable_anchor_text
            self.markdown_lines.append(f"[{link_text}]({href})")
        elif node.name in ['ac:link']:
            # Convert ac:link node to markdown link
            markdown_link = self.convert_ac_link(node)
            self.markdown_lines.append(markdown_link)
        elif node.name in ['ri:page']:
            content_title = node.get('content-title', '#')
            self.markdown_lines.append(content_title)
        elif node.name in ['ac:link-body']:
            # ac:link-body is used in ac:link, we can process it as a regular text
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['ac:adf-fragment-mark']:
            """
            Source:
                <ac:adf-fragment-mark>
                    <ac:adf-fragment-mark-detail name="Table 1" local-id="42cfbf5f-5c57-44da-8f07-e1ea866a985a"/>
                </ac:adf-fragment-mark>
            
            Target:
                <a id="table-1"></a>
                - Use lower cases for fragment names.
                - Use hyphen for spaces and underscores.
            """
            adf_fragment_mark_detail = node.find('ac:adf-fragment-mark-detail')
            if adf_fragment_mark_detail:
                fragment_name = adf_fragment_mark_detail.get('name')
                fragment_name = fragment_name.lower().replace(' ', '-').replace('_', '-')
                self.markdown_lines.append(f'<a id="{fragment_name}"></a>')
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
            or
            <ac:emoticon ac:name="blue-star" ac:emoji-shortname=":white_check_mark:"
                         ac:emoji-id="2705" ac:emoji-fallback="✅"/>
            """
            # First check ac:emoji-fallback attribute (may already be an emoji character)
            fallback = node.get('emoji-fallback', '')
            shortname = node.get('emoji-shortname', '')
            
            # Check if fallback is already an emoji character (not in shortname format)
            if fallback and not fallback.startswith(':'):
                # Already an actual emoji character
                self.markdown_lines.append(fallback)
            elif shortname:
                # Convert shortname to actual emoji
                if EMOJI_AVAILABLE:
                    # Use emoji library to convert shortname to actual emoji
                    emoji_char = emoji.emojize(shortname, language='alias')
                    if emoji_char != shortname:
                        # Conversion successful (converted to actual emoji)
                        self.markdown_lines.append(emoji_char)
                    else:
                        # Conversion failed (use fallback or shortname as-is)
                        if fallback:
                            self.markdown_lines.append(fallback)
                        else:
                            self.markdown_lines.append(shortname)
                else:
                    # emoji library not available, use fallback or shortname
                    if fallback:
                        self.markdown_lines.append(fallback)
                    else:
                        self.markdown_lines.append(shortname)
            elif fallback:
                # No shortname but fallback is available
                self.markdown_lines.append(fallback)
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

        if node.name in self._debug_tags:
            self.markdown_lines.append(f'</{node.name}>')
        return

    def markdown_of_children(self, node):
        """
        Convert children nodes as a single line Markdown
        :param node:
        :return:
        """
        markdown = []
        for child in node.children:
            markdown.append(SingleLineParser(child).as_markdown)
        return ''.join(markdown)

    def convert_ac_link(self, node: Tag) -> str:
        """
        Convert ac:link node to markdown link format

        Handles various types of Confluence links and generates appropriate markdown output:

        1. Internal Page Link (target page in pages.yaml):
           XHTML:
               <ac:link>
                   <ri:page ri:content-title="User Guide"/>
                   <ac:link-body>User Guide</ac:link-body>
               </ac:link>
           Output:
               [User Guide](../../user-guide)

        2. External Page Link with pageId (target page in page.v1.yaml link mapping):
           XHTML:
               <ac:link>
                   <ri:page ri:space-key="QCP" ri:content-title="QueryPie Architecture (KO)"/>
                   <ac:link-body>QueryPie Architecture</ac:link-body>
               </ac:link>
           Output:
               [QueryPie Architecture](https://querypie.atlassian.net/wiki/spaces/QCP/pages/400064797)

        3. External Page Link without pageId (fallback to space overview):
           XHTML:
               <ac:link>
                   <ri:page ri:space-key="QCP" ri:content-title="Unknown Page"/>
                   <ac:link-body>Unknown Page</ac:link-body>
               </ac:link>
           Output:
               [Unknown Page](https://querypie.atlassian.net/wiki/spaces/QCP/overview)

        4. Space Link:
           XHTML:
               <ac:link>
                   <ri:space ri:space-key="QCP"/>
                   <ac:link-body>Confluence Space</ac:link-body>
               </ac:link>
           Output:
               [Confluence Space](https://querypie.atlassian.net/wiki/spaces/QCP/overview)

        5. Link with Anchor Fragment:
           XHTML:
               <ac:link ac:anchor="section-name">
                   <ri:page ri:content-title="My Dashboard"/>
                   <ac:link-body>My Dashboard</ac:link-body>
               </ac:link>
           Output:
               [My Dashboard | section-name](../../my-dashboard#section-name)

        6. Error Case (no space key):
           XHTML:
               <ac:link>
                   <ri:page ri:content-title="Missing Page"/>
                   <ac:link-body>Missing Page</ac:link-body>
               </ac:link>
           Output:
               [Missing Page](#link-error)

        Args:
            node (Tag): BeautifulSoup Tag object representing ac:link node

        Returns:
            str: Markdown link in format [link_body](href) or [link_body | anchor](href#fragment)
        """
        link_body = '(ERROR: Link body not found)'
        anchor = node.get('anchor', '')

        # Process anchor fragment
        if anchor:
            decoded_anchor = ' | ' + unquote(anchor)
            lowercased_fragment = '#' + anchor.lower()
        else:
            decoded_anchor = ''
            lowercased_fragment = ''

        href = '#'

        # Process child nodes to extract link body and determine href
        for child in node.children:
            if isinstance(child, Tag) and child.name == 'ac:link-body':
                link_body = SingleLineParser(child).as_markdown

            elif isinstance(child, Tag) and child.name == 'ri:space':
                # Handle space links: <ac:link><ri:space ri:space-key="QCP" /></ac:link>
                space_key = child.get('space-key', '')
                if space_key:
                    href = f'https://querypie.atlassian.net/wiki/spaces/{space_key}/overview'
                    logging.info(f"Generated Confluence space overview link for space '{space_key}': {href}")
                else:
                    href = '#link-error'
                    logging.warning(f"No space key found in ri:space tag, using error anchor: {href}")

            elif isinstance(child, Tag) and child.name == 'ri:page':
                target_title = child.get('content-title', '')
                space_key = child.get('space-key', '')

                # Check if the target page is in pages.yaml
                target_page = PAGES_BY_TITLE.get(target_title)

                if target_page:
                    # Internal link - use relative path
                    href = relative_path_to_titled_page(target_title)
                else:
                    # External link - resolve using pageId from link mapping
                    # Get link_body explicitly to ensure we have the correct text for lookup
                    link_body_node = node.find('ac:link-body')
                    current_link_body = SingleLineParser(link_body_node).as_markdown if link_body_node else link_body
                    href = resolve_external_link(current_link_body, space_key, target_title)

        return f'[{link_body}{decoded_anchor}]({href}{lowercased_fragment})'

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
            ![image-20240806-095511.png](image-20240806-095511.png){width="760"}
        """
        logging.debug(f"Processing Confluence image: {node}")

        # Extract width attribute if custom-width is true
        width = None
        custom_width = node.get('custom-width', 'false')
        if custom_width == 'true':
            width = node.get('width', '')
            if width:
                logging.debug(f"Using custom width: {width}")

        # Extract align attribute
        align = node.get('align', 'center')

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

        # Find matching attachment in attachments list
        markdown = ''
        image_filename = unicodedata.normalize('NFC', image_filename)
        if image_filename:
            attachments = get_attachments()
            for it in attachments:
                if it.original == image_filename:
                    it.used = True
                    markdown = it.as_markdown(width=width, align=align)
                    break

        if not markdown:
            # If no matching attachment found, use the filename as fallback
            logging.warning(f'No matching attachment found for filename: {image_filename}')
            markdown = f'[{image_filename}]()'

        # Add the image in Markdown format
        self.markdown_lines.append(markdown)


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

    @property
    def is_standalone_dash(self):
        """
        Check if the node contains only a plain standalone dash character.

        This is used to detect table cells with just '-' which would be
        incorrectly interpreted as a markdown list marker by MDX.

        Returns False if the dash has any formatting (italic, bold, etc.)
        since formatted dashes render as *-* or **-** which are not list markers.
        """
        # First check: text content must be just '-'
        if self.node.get_text(strip=True) != '-':
            return False

        # Second check: must not have formatting tags (em, strong, etc.)
        # If there are formatting tags, the markdown output will be *-* or **-**
        # which won't be interpreted as a list marker
        formatting_tags = {'em', 'strong', 'b', 'i', 'u', 'code'}
        if any(self.node.find(tag) for tag in formatting_tags):
            return False

        return True

    def append_empty_line_unless_first_child(self, node):
        # Convert generator to list to check length
        children_list = list(node.parent.children)
        if len(children_list) == 1:
            if self._debug_markdown:
                self.markdown_lines.append(f'<{node.name} the-only-child=true>\n')
            pass  # The only child means the first child.
        elif len(children_list) > 2:
            first_sibling = children_list[0]
            if node == first_sibling:
                if self._debug_markdown:
                    self.markdown_lines.append(f'<{node.name} first-sibling=true>\n')
                pass
            elif len(self.markdown_lines) == 0:
                pass
            elif len(self.markdown_lines) > 0 and self.markdown_lines[-1] == '\n':
                if self._debug_markdown:
                    self.markdown_lines.append(f'<{node.name} first-sibling=false [-1]({repr(self.markdown_lines[-1])}) == "\\n">\n')
                pass
            else:
                if self._debug_markdown:
                    self.markdown_lines.append('<empty-line>\n')
                    self.markdown_lines.append(f'<{node.name} empty-line>\n')
                else:
                    self.markdown_lines.append('\n')

    def convert_recursively(self, node):
        """Recursively convert child nodes to Markdown."""
        if isinstance(node, NavigableString):
            if node.parent.name == '[document]' and len(node.text.strip()) == 0:
                pass
            else:
                logging.warning(f"MultiLineParser: Unexpected NavigableString {repr(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
                self.markdown_lines.append(f"MultiLineParser: Unexpected NavigableString {repr(node)} of from {ancestors(node)} in {INPUT_FILE_PATH}")
            return

        logging.debug(f"MultiLineParser: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        attr_name = node.get('name', '(none)')
        if node.name in [
            '[document]',  # Start processing from the body of the document
            'html', 'body',
            'ac:layout', 'ac:layout-section', 'ac:layout-cell',  # Skip layout tags
        ]:
            for child in node.children:
                self.convert_recursively(child)
        elif node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Headings can exist in a <Callout> block.
            self.append_empty_line_unless_first_child(node)
            self.markdown_lines.append(SingleLineParser(node).as_markdown + '\n')
            self.markdown_lines.append('\n')
        elif node.name in ['ac:structured-macro'] and StructuredMacroToCallout(node).applicable:
            self.append_empty_line_unless_first_child(node)
            self.markdown_lines.extend(StructuredMacroToCallout(node).as_markdown)
        elif node.name == 'ac:adf-extension' and AdfExtensionToCallout(node).applicable:
            self.append_empty_line_unless_first_child(node)
            self.markdown_lines.extend(AdfExtensionToCallout(node).as_markdown)
        elif node.name in ['ac:structured-macro'] and attr_name in ['code']:
            self.convert_structured_macro_code(node)
        elif node.name in ['ac:structured-macro'] and attr_name in ['expand']:
            self.convert_structured_macro_expand(node)
        elif node.name in ['ac:structured-macro'] and attr_name in ['view-file']:
            self.convert_structured_macro_view_file(node)
        elif node.name in ['ac:structured-macro'] and attr_name in ['toc']:
            # Table of contents macro, we can skip it, as toc is provided by the Markdown renderer by default
            logging.info("Skipping TOC macro")
        elif node.name in ['ac:structured-macro'] and attr_name in ['children']:
            logging.info(f"Unsupported {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'(Unsupported xhtml node: &lt;ac:structured-macro name="children"&gt;)\n')
        elif node.name in ['blockquote']:
            self.append_empty_line_unless_first_child(node)
            markdown = []
            for child in node.children:
                markdown.extend(MultiLineParser(child).as_markdown)
            lines = ''.join(markdown).splitlines()
            for to_quote in lines:
                self.markdown_lines.append(f'> {to_quote}')
        elif node.name in [
            'ac:rich-text-body',  # Child of <ac:structured-macro name="panel">
            'ac:adf-content',  # Child of <ac:adf-extension>
        ]:
            for child in node.children:
                self.convert_recursively(child)
        elif node.name == 'table':
            native_markdown = TableToNativeMarkdown(node)
            if native_markdown.applicable:
                self.append_empty_line_unless_first_child(node)
                self.markdown_lines.extend(native_markdown.as_markdown)
            else:
                self.append_empty_line_unless_first_child(node)
                self.markdown_lines.extend(TableToHtmlTable(node).as_markdown)
        elif node.name in ['p', 'div']:
            self.append_empty_line_unless_first_child(node)
            child_markdown = []
            for child in node.children:
                if isinstance(child, NavigableString):
                    # Problem: A paragraph was in a too long line.
                    # Resolve:
                    # - Split a paragraph into sentences. And arrange one sentence in each line.
                    single_line = SingleLineParser(child).as_markdown
                    # Preserve a leading whitespace in single_line
                    if single_line[0].isspace():
                        child_markdown.append(' ')
                    multiple_lines = split_into_sentences(single_line)
                    if multiple_lines:
                        child_markdown.extend(s + '\n' for s in multiple_lines[:-1])
                        child_markdown.append(multiple_lines[-1])
                    # Preserve an ending whitespace in single_line
                    if single_line[-1].isspace():
                        child_markdown.append(' ')
                elif SingleLineParser(child).applicable:
                    child_markdown.append(SingleLineParser(child).as_markdown)
                else:
                    if self._debug_markdown:
                        child_markdown.append(f'<{child.name}>')
                    child_markdown.extend(MultiLineParser(child).as_markdown)
                    if self._debug_markdown:
                        child_markdown.append(f'</{child.name}>')
            # Add an empty line after paragraphs
            self.markdown_lines.append(''.join(child_markdown).strip() + '\n')
        elif node.name in ['span']:
            self.markdown_lines.append(SingleLineParser(node).as_markdown)
        elif node.name in ['br']:
            # <br/> is a line break. Just keep using <br/>.
            # Append '\n' for <br/> in MultiLineParser.
            self.markdown_lines.append("<br/>\n")
        elif node.name in ['ul', 'ol']:
            self.append_empty_line_unless_first_child(node)
            self.convert_ul_ol(node)
        elif node.name in ['ac:image']:
            self.append_empty_line_unless_first_child(node)
            self.convert_image(node)
        elif node.name in ['a']:
            self.markdown_lines.append(SingleLineParser(node).as_markdown)
        elif node.name in ['hr']:
            # Using --- after a sentence means an H2 heading.
            # To prevent ambiguity with headings, use ______ for a horizontal rule.
            self.markdown_lines.append(f'______\n')
        else:
            logging.warning(f"MultiLineParser: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]\n')
            for child in node.children:
                self.convert_recursively(child)

    def convert_ul_ol(self, node):
        self.list_stack.append(node.name)
        counter = 1
        for child in node.children:
            if child.name == 'li':
                self.convert_li(child, node.name, counter)
                counter += 1
            else:
                if isinstance(child, NavigableString):
                    if len(child.text.strip()) > 0:
                        logging.warning(f'Skip extracting NavigableString({repr(child)}) of <{node.name}> from {ancestors(node)} in {INPUT_FILE_PATH}')
                    else:
                        logging.debug(f'Skip extracting NavigableString({repr(child)}) of <{node.name}> from {ancestors(node)} in {INPUT_FILE_PATH}')
                else:
                    logging.warning(f'Skip extracting <{child.name}> of <{node.name}> from {ancestors(node)} in {INPUT_FILE_PATH}')
        self.list_stack.pop()
        return

    def convert_li(self, node, list_type, counter=None):
        indent = " " * 4 * (len(self.list_stack) - 1)
        if list_type == 'ul':
            prefix = f"{indent}* "
            prefix_for_children = f"{indent}  "
        else:
            prefix = f"{indent}{counter}. "
            prefix_for_children = f"{indent}  "

        # Process each child element separately to handle mixed content
        li_itself = []
        child_markdown = []
        for child in node.children:
            attr_name = child.get('name', '(none)') if not isinstance(child, NavigableString) else '(none)'
            if isinstance(child, NavigableString):
                if child.text.strip():  # Only process non-empty text nodes
                    li_itself.append(SingleLineParser(child).as_markdown)
            elif child.name == 'p':
                # Process paragraph content
                if len(li_itself) > 0:
                    li_itself.append('<br/>')
                li_itself.append(SingleLineParser(child).as_markdown)
            elif child.name == 'ac:image':
                # Process image separately using MultiLineParser
                image_markdown = MultiLineParser(child).as_markdown
                child_markdown.extend(image_markdown)
            elif child.name in ['ul', 'ol']:
                pass  # Will be processed later in this method
            elif child.name in ['ac:structured-macro'] and attr_name in ['code']:
                code_markdown = MultiLineParser(child).as_markdown
                child_markdown.extend(code_markdown)
            else:
                child_markdown.append(f'(Unexpected node name="{child.name}" ac:name="{attr_name}")\n')

        logging.debug(f'li_itself={li_itself}')
        logging.debug(f'child_markdown={child_markdown}')

        itself = ' '.join(li_itself)
        self.markdown_lines.append(f'{prefix}{itself}\n')
        for line in child_markdown:
            self.markdown_lines.append(prefix_for_children + line)

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
            ![image-20240806-095511.png](image-20240806-095511.png){width="760"}
            *How QueryPie Works*
        """
        logging.debug(f"Processing Confluence image: {node}")

        # Extract image attributes
        align = node.get('align', 'center')
        alt_text = node.get('alt', '')

        # Extract width attribute if custom-width is true
        width = None
        custom_width = node.get('custom-width', 'false')
        if custom_width == 'true':
            width = node.get('width', '')
            if width:
                logging.debug(f"Using custom width: {width}")

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

        markdown = ''
        image_filename = unicodedata.normalize('NFC', image_filename)
        if image_filename:
            attachments = get_attachments()
            for it in attachments:
                if it.original == image_filename:
                    it.used = True
                    markdown = it.as_markdown(caption_text, width, align)
                    break

        if not markdown:
            # If no matching attachment found, use the filename as fallback
            logging.warning(f'No matching attachment found for filename: {image_filename}')
            markdown = f'[{image_filename}]()'

        # Add the image in Markdown format
        self.markdown_lines.append(f'<figure data-layout="{align}" data-align="{align}">\n')
        self.markdown_lines.append(f"{markdown}\n")

        # Add caption if present
        if caption_text:
            self.markdown_lines.append(f'<figcaption>\n')
            self.markdown_lines.append(f'{caption_text}\n')
            self.markdown_lines.append(f"</figcaption>\n")

        self.markdown_lines.append(f'</figure>\n')

    def convert_structured_macro_code(self, node):
        # Find language parameter and code content
        language = ""
        cdata = 'TODO(JK): Error in converting <structured-macro name="code">'

        # Look for language parameter
        language_param = node.find('ac:parameter', {'name': 'language'})
        if language_param:
            language = language_param.get_text()
        self.markdown_lines.append(f"```{language}\n")

        # Look for code content in the CDATA section
        plain_text_body = node.find('ac:plain-text-body')
        if plain_text_body:
            # Extract CDATA content
            for item in plain_text_body.contents:
                if isinstance(item, CData):
                    cdata = str(item)  # Convert CData object to string
                    break
        for line in cdata.rstrip('\n').split('\n'):
            self.markdown_lines.append(f"{line}\n")
        self.markdown_lines.append("```\n")

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

    def convert_structured_macro_view_file(self, node):
        """
        <ac:structured-macro ac:name="view-file" ac:schema-version="1" ac:macro-id="0ca43a9e-a4e1-4b7a-ad33-9a40ac673203">
            <ac:parameter ac:name="name">
                <ri:attachment ri:filename="994_external.json" ri:version-at-save="1"/>
            </ac:parameter>
        </ac:structured-macro>

        📎 [994_external.json](./994_external.json)
        """
        filename = ""
        name_parameter = node.find('ac:parameter', {'name': 'name'})
        if name_parameter:
            attachment = name_parameter.find('ri:attachment')
            if attachment:
                filename = attachment.get('filename', '')
        self.markdown_lines.append(f":paperclip: [{filename}]({filename})\n")


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
            'ac:adf-fragment-mark', 'ac:adf-fragment-mark-detail',
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
            logging.warning(f"TableToNativeMarkdown: Unexpected NavigableString {repr(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(node.text)
            return

        logging.debug(f"TableToNativeMarkdown: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        if node.name in ['table']:
            self.convert_table(node)
        else:
            logging.warning(f"TableToNativeMarkdown: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]\n')
            for child in node.children:
                self.convert_recursively(child)

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
        self.table_data_to_markdown(table_data)

    def table_data_to_markdown(self, table_data):
        if not table_data or not any(table_data):
            return

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

        # Header row
        header_row = "| " + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(normalized_data[0])) + " |\n"
        self.markdown_lines.append(header_row)

        # Separator row
        separator = "| " + " | ".join("-" * col_widths[i] for i in range(num_cols)) + " |\n"
        self.markdown_lines.append(separator)

        # Data rows
        for row in normalized_data[1:]:
            data_row = "| " + " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)) + " |\n"
            self.markdown_lines.append(data_row)

        return


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
            logging.warning(f"TableToHtmlTable: Unexpected NavigableString {repr(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(node.text)
            return

        logging.debug(f"TableToHtmlTable: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")

        if node.name in ['table', 'thead', 'tbody', 'tfoot', 'tr', 'colgroup']:
            """Convert table node to HTML table markup."""
            attrs = get_html_attributes(node)
            self.markdown_lines.append(f"<{node.name}{attrs}>\n")

            for child in node.children:
                if not isinstance(child, NavigableString):
                    self.convert_recursively(child)

            self.markdown_lines.append(f"</{node.name}>\n")
        elif node.name in ['th', 'td']:
            attrs = get_html_attributes(node)
            self.markdown_lines.append(f"<{node.name}{attrs}>\n")

            for child in node.children:
                if isinstance(child, NavigableString):
                    self.markdown_lines.append(SingleLineParser(child).as_markdown + '\n')
                elif SingleLineParser(child).applicable:
                    self.markdown_lines.append(SingleLineParser(child).as_markdown + '\n')
                elif MultiLineParser(child).is_standalone_dash:
                    # Wrap dash in <p> to prevent MDX interpreting it as a list marker
                    self.markdown_lines.append(f'<p>-</p>\n')
                else:
                    self.markdown_lines.extend(MultiLineParser(child).as_markdown)

            self.markdown_lines.append(f"</{node.name}>\n")
        elif node.name == 'col':
            """Convert col node to HTML col markup."""
            attrs = get_html_attributes(node)
            self.markdown_lines.append(f"<col{attrs}/>\n")
        elif SingleLineParser(node).applicable:
            # <ac:adf-fragment-mark> could be converted.
            self.markdown_lines.append(SingleLineParser(node).as_markdown + '\n')
        else:
            logging.warning(f"TableToHtmlTable: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]\n')
            for child in node.children:
                self.convert_recursively(child)


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
            logging.warning(f"StructuredMacroToCallout: Unexpected NavigableString {repr(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            # Do not append unexpected NavigableString to markdown_lines.
            return

        logging.debug(f"StructuredMacroToCallout: type={type(node).__name__}, name={node.name}, value={repr(node.text)}")
        attr_name = node.get('name', '')
        if node.name in ['ac:structured-macro'] and attr_name in ['tip', 'info', 'note', 'warning']:
            # https://nextra.site/docs/built-ins/callout
            # Confluence has broken namings of panels.
            if attr_name == 'tip':  # success
                self.markdown_lines.append('<Callout type="default">\n')
            elif attr_name == 'info':  # info
                self.markdown_lines.append('<Callout type="info">\n')
            elif attr_name == 'note':  # note
                self.markdown_lines.append('<Callout type="important">\n')
            elif attr_name == 'warning':  # error - a broken name
                self.markdown_lines.append('<Callout type="error">\n')
            else:
                self.markdown_lines.append(f'<Callout> {"{"}/* <ac:structured-macro ac:name="{attr_name}"> */{"}"}\n')
                logging.warning(f"Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")

            for child in node.children:
                self.markdown_lines.extend(MultiLineParser(child).as_markdown)

            self.markdown_lines.append('</Callout>\n')
        elif node.name in ['ac:structured-macro'] and attr_name in ['panel']:
            parameter = node.find('ac:parameter', {'name': 'panelIconText'})
            rich_text_body = node.find('ac:rich-text-body')
            # https://nextra.site/docs/built-ins/callout
            # Confluence has broken namings of panels.
            if parameter:
                self.markdown_lines.append(f'<Callout type="info" emoji="{parameter.text}">\n')
            else:
                self.markdown_lines.append('<Callout>\n')
                logging.warning(
                    f'Cannot find <ac:parameter ac:name="panelIconText"> under {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}')

            if rich_text_body:
                self.markdown_lines.extend(MultiLineParser(rich_text_body).as_markdown)
            else:
                logging.warning(
                    f'Cannot find <ac:rich-text-body> under {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}')

            self.markdown_lines.append('</Callout>\n')
        else:
            logging.warning(f"StructuredMacroToCallout: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]\n')
            for child in node.children:
                self.convert_recursively(child)


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
            logging.warning(f"AdfExtensionToCallout: Unexpected NavigableString {repr(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
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
                self.markdown_lines.append('<Callout type="important">\n')
            else:
                self.markdown_lines.append('<Callout>\n')
                logging.warning(
                    f'Unexpected panel-type of "{panel_type}" in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}')

            adf_content = node.find('ac:adf-content')
            if adf_content:
                self.markdown_lines.extend(MultiLineParser(adf_content).as_markdown)
            else:
                logging.warning(f"No <ac:adf-content> in {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")

            self.markdown_lines.append('</Callout>\n')
        elif node.name in ['ac:adf-fallback']:
            pass  # Ignore <ac:adf-fallback>
        else:
            logging.warning(f"AdfExtensionToCallout: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {INPUT_FILE_PATH}")
            self.markdown_lines.append(f'[{node.name}]\n')
            for child in node.children:
                self.convert_recursively(child)


class ConfluenceToMarkdown:
    def __init__(self, html_content: str):
        self.markdown_lines = []
        self._imports = {}
        self._debug_markdown = False

        # Parse HTML with BeautifulSoup
        self.soup = BeautifulSoup(html_content, 'html.parser')

    @property
    def imports(self):
        markdown = []
        if 'Callout' in self._imports and self._imports['Callout']:
            markdown.append("import { Callout } from 'nextra/components'\n")
        if len(markdown) > 0:
            markdown.append("\n")  # Add an empty line after imports
        return markdown

    @property
    def remark(self):
        remarks = []
        page_v1 = get_page_v1()
        if page_v1 and page_v1.get("title"):
            title = clean_text(page_v1.get("title")).strip()
            # repr() generates a valid value of string for yaml.
            remarks.append(f'title: {repr(title)}\n')

        if len(remarks) > 0:
            return ["---\n"] + remarks + ["---\n", "\n"]
        else:
            return []

    @property
    def title(self):
        """Get document title and format it as h1 heading for Nextra"""
        page_v1 = get_page_v1()
        if page_v1 and page_v1.get("title"):
            title = clean_text(page_v1.get("title")).strip()
            if title:
                return [f"# {title}\n", "\n"]
        return []

    def add_import(self, module_name, condition=True):
        """Add an import statement to the list of imports."""
        if condition:
            self._imports[module_name] = True
        else:
            self._imports[module_name] = False

    def load_attachments(self, input_dir: str, output_dir: str, public_dir: str,
                         skip_image_copy: bool = False) -> None:
        # Find all ac:image nodes first
        ac_image_nodes = self.soup.find_all('ac:image')
        attachments: List[Attachment] = []
        for ac_image in ac_image_nodes:
            # Find ri:attachment nodes within each ac:image
            attachment_nodes = ac_image.find_all('ri:attachment')
            for node in attachment_nodes:
                logging.debug(f"add attachment of <ac:image>{node}")
                attachment = Attachment(node, input_dir, output_dir, public_dir)
                if not skip_image_copy:
                    attachment.copy_to_destination()
                attachments.append(attachment)

        logging.debug(f"attachments: {attachments}")
        set_attachments(attachments)

    def as_markdown(self):
        if StructuredMacroToCallout(self.soup).has_applicable_nodes:
            self.add_import('Callout')
        elif AdfExtensionToCallout(self.soup).has_applicable_nodes:
            self.add_import('Callout')

        # Add document title at the beginning if available
        self.markdown_lines.extend(self.title)
        # Start conversion
        self.markdown_lines.extend(MultiLineParser(self.soup).as_markdown)
        # self.process_node(soup)

        # Join all Markdown lines and return
        return ''.join(chain(self.remark, self.imports, self.markdown_lines))


def generate_meta_from_children(input_dir: str, output_file_path: str, pages_by_id: PagesDict) -> None:
    """Generate a Nextra sidebar _meta.ts file using children.v2.yaml in input_dir.
    - Reads children.v2.yaml if present.
    - Sorts children by childPosition.
    - Uses pages_by_id to resolve each child's filename slug from pages.yaml path.
    - Warns when a child id is not found in pages_by_id.
    - Validates that a corresponding MDX file (slug_key.mdx) exists next to _meta.ts; otherwise warns and skips.
    - Writes _meta.ts under dirname(output_file_path)/stem/_meta.ts.
    Swallows exceptions with logging to keep conversion resilient.
    """
    try:
        children_yaml_path = os.path.join(input_dir, 'children.v2.yaml')
        if os.path.exists(children_yaml_path):
            with open(children_yaml_path, 'r', encoding='utf-8') as yf:
                children_data = yaml.safe_load(yf)
            results = children_data.get('results') if isinstance(children_data, dict) else None
            if isinstance(results, list) and len(results) > 0:
                def _pos(item: dict) -> int:
                    try:
                        return int(item.get('childPosition', 0))
                    except Exception:
                        return 0
                ordered = sorted(results, key=_pos)

                # Determine where _meta.ts and child mdx files should live
                meta_dir = os.path.join(os.path.dirname(output_file_path), Path(output_file_path).stem)
                os.makedirs(meta_dir, exist_ok=True)

                entries: List[str] = []
                for child in ordered:
                    if not isinstance(child, dict):
                        continue
                    child_id = str(child.get('id')) if child.get('id') is not None else None
                    title = clean_text(child.get('title'))
                    if not child_id:
                        logging.warning(f"children.v2.yaml entry missing id: {child}")
                        continue
                    page_info = pages_by_id.get(child_id)
                    if not page_info:
                        logging.warning(f"Child page id {child_id} not found in pages.yaml while generating _meta.ts from {children_yaml_path}")
                        # Continue but skip since we cannot determine filename
                        continue
                    # Determine slug/filename from page_info.path if available
                    slug_key: Optional[str] = None
                    try:
                        path_list = page_info.get('path') if isinstance(page_info, dict) else None
                        if isinstance(path_list, list) and len(path_list) > 0:
                            slug_key = str(path_list[-1])
                    except Exception:
                        slug_key = None
                    if not slug_key:
                        logging.warning(f"Child page id {child_id} has no valid path in pages.yaml; skipping entry in _meta.ts")
                        continue

                    key_repr = f"'{slug_key}'"
                    title_repr = (title or '').strip().replace("'", "\\'")
                    entries.append(f"  {key_repr}: '{title_repr}',")

                if entries:
                    meta_path = os.path.join(meta_dir, '_meta.ts')
                    content = 'export default {\n' + "\n".join(entries) + '\n};\n'
                    with open(meta_path, 'w', encoding='utf-8') as mf:
                        mf.write(content)
                    logging.info(f"Generated sidebar meta at {meta_path} from {children_yaml_path}")
                else:
                    logging.info("No sidebar entries generated: children list empty after processing")
            else:
                logging.info("children.v2.yaml has no 'results' or it is empty; skipping _meta.ts")
        else:
            logging.debug("No children.v2.yaml found; skipping _meta.ts generation")
    except Exception as meta_err:
        logging.error(f"Failed to generate _meta.ts: {meta_err}")


def main():
    parser = argparse.ArgumentParser(description='Convert Confluence XHTML to Markdown')
    parser.add_argument('input_file', help='Input XHTML file path')
    parser.add_argument('output_file', help='Output Markdown file path')
    parser.add_argument('--public-dir',
                        default='./public',
                        help='/public directory path')
    parser.add_argument('--attachment-dir',
                        help='Directory to save attachments (default: output file directory)')
    parser.add_argument('--skip-image-copy', action='store_true',
                        help='이미지 파일 복사를 생략 (경로만 지정대로 생성)')
    parser.add_argument('--log-level',
                        choices=['debug', 'info', 'warning', 'error', 'critical'],
                        default='info',
                        help='Set the logging level (default: info)')
    args = parser.parse_args()

    # Configure logging with the specified level
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(level=log_level, format='%(levelname)s - %(funcName)s:%(lineno)d - %(message)s')

    # Store the input file path in a global variable
    global INPUT_FILE_PATH, OUTPUT_FILE_PATH, LANGUAGE

    INPUT_FILE_PATH = os.path.normpath(args.input_file)  # Normalize path for cross-platform compatibility
    OUTPUT_FILE_PATH = os.path.normpath(args.output_file)

    input_dir = os.path.dirname(INPUT_FILE_PATH)
    # Set an attachment directory if provided
    if args.attachment_dir:
        output_dir = args.attachment_dir
        logging.info(f"Using attachment directory: {output_dir}")
    else:
        output_file_stem = Path(args.output_file).stem
        output_dir = os.path.join(os.path.dirname(args.output_file), output_file_stem)
        logging.info(f"Using default attachment directory: {output_dir}")

    # Extract language code from the output file path
    path_parts = OUTPUT_FILE_PATH.split(os.sep)

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

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Replace XML namespace prefixes
        html_content = re.sub(r'\sac:', ' ', html_content)
        html_content = re.sub(r'\sri:', ' ', html_content)

        # Load pages.yaml to get the current page's path
        pages_yaml_path = os.path.join(input_dir, '..', 'pages.yaml')
        global PAGES_BY_TITLE
        load_pages_yaml(pages_yaml_path, PAGES_BY_TITLE, PAGES_BY_ID)

        # Load page.v1.yaml from the same directory as the input file
        page_v1: Optional[PageV1] = load_page_v1_yaml(os.path.join(input_dir, 'page.v1.yaml'))
        set_page_v1(page_v1)

        # Build link mapping from page.v1.yaml for external link pageId resolution
        global GLOBAL_LINK_MAPPING
        GLOBAL_LINK_MAPPING = build_link_mapping(page_v1)

        converter = ConfluenceToMarkdown(html_content)
        converter.load_attachments(input_dir, output_dir, args.public_dir,
                                   skip_image_copy=args.skip_image_copy)
        markdown_content = converter.as_markdown()

        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        attachments = get_attachments()
        for it in attachments:
            if it.used:
                logging.debug(f'Attachment {it} is used.')
            else:
                logging.warning(f'Attachment {it} is NOT used.')

        # Generate _meta.ts from children.v2.yaml to preserve child order for Netra sidebar
        generate_meta_from_children(input_dir, OUTPUT_FILE_PATH, PAGES_BY_ID)

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
