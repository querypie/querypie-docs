#!/usr/bin/env python3
"""
Converter Context Module

Provides global state, type definitions, and utility functions
for the Confluence XHTML to Markdown conversion process.
"""

import logging
import os
import re
import unicodedata
from datetime import datetime
from typing import Optional, Dict, List, Any, TypedDict
from urllib.parse import unquote, urlparse

import yaml
from bs4 import BeautifulSoup, NavigableString

from text_utils import clean_text

try:
    import emoji
except ImportError:
    raise SystemExit(
        "Required package 'emoji' is not installed.\n"
        "Run: pip install 'emoji>=2.8.0'"
    )


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
GLOBAL_ATTACHMENTS: List = []
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


def get_attachments() -> List:
    """Get the current attachments list"""
    global GLOBAL_ATTACHMENTS
    return GLOBAL_ATTACHMENTS


def set_page_v1(page_v1: Optional[PageV1]) -> None:
    """Set the current page_v1 data"""
    global GLOBAL_PAGE_V1
    GLOBAL_PAGE_V1 = page_v1


def set_attachments(attachments: List) -> None:
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
