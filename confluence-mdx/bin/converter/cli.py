#!/usr/bin/env python3
"""
CLI entry point for the Confluence XHTML to Markdown converter.

Provides the command-line interface for converting Confluence XHTML exports
to clean Markdown, including argument parsing and conversion orchestration.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List

import yaml

# Resolve project root (confluence-mdx/) from this script's location
# bin/converter/cli.py -> .parent=converter/ -> .parent=bin/ -> .parent=confluence-mdx/
_SCRIPT_DIR = Path(__file__).resolve().parent.parent  # confluence-mdx/bin/
_PROJECT_DIR = _SCRIPT_DIR.parent                     # confluence-mdx/

# Ensure bin/ is on sys.path when run as a script (e.g. bin/converter/cli.py)
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import converter.context as ctx
from converter.context import (
    PAGES_BY_TITLE, PAGES_BY_ID,
    PagesDict, PageV1,
    load_pages_yaml, load_page_v1_yaml, build_link_mapping,
    set_page_v1, get_page_v1, get_attachments,
    clean_text,
)
from converter.core import ConfluenceToMarkdown


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
                        default=str(_PROJECT_DIR / 'public'),
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

    # Store the input file path in shared context
    ctx.INPUT_FILE_PATH = os.path.normpath(args.input_file)  # Normalize path for cross-platform compatibility
    ctx.OUTPUT_FILE_PATH = os.path.normpath(args.output_file)

    input_dir = os.path.dirname(ctx.INPUT_FILE_PATH)
    # Set an attachment directory if provided
    if args.attachment_dir:
        output_dir = args.attachment_dir
        logging.info(f"Using attachment directory: {output_dir}")
    else:
        output_file_stem = Path(args.output_file).stem
        output_dir = os.path.join(os.path.dirname(args.output_file), output_file_stem)
        logging.info(f"Using default attachment directory: {output_dir}")

    # Extract language code from the output file path
    path_parts = ctx.OUTPUT_FILE_PATH.split(os.sep)

    # Look for 2-letter language code in the path
    detected_language = 'en'  # Default to English
    for part in path_parts:
        if len(part) == 2 and part.isalpha():
            # Check if it's a known language code
            if part in ['ko', 'ja', 'en']:
                detected_language = part
                break

    # Update shared LANGUAGE variable
    ctx.LANGUAGE = detected_language
    logging.info(f"Detected language from output path: {ctx.LANGUAGE}")

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 원본 XHTML 보존 — sidecar mapping에서 사용
        xhtml_original = html_content

        # Load pages.yaml to get the current page's path
        pages_yaml_path = os.path.join(input_dir, '..', 'pages.yaml')
        load_pages_yaml(pages_yaml_path, PAGES_BY_TITLE, PAGES_BY_ID)

        # Load page.v1.yaml from the same directory as the input file
        page_v1: Optional[PageV1] = load_page_v1_yaml(os.path.join(input_dir, 'page.v1.yaml'))
        set_page_v1(page_v1)

        # Build link mapping from page.v1.yaml for external link pageId resolution
        ctx.GLOBAL_LINK_MAPPING = build_link_mapping(page_v1)

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

        # Sidecar mapping 생성 (실패해도 변환 자체는 차단하지 않음)
        try:
            from converter.sidecar_mapping import generate_sidecar_mapping
            generate_sidecar_mapping(
                xhtml_content=xhtml_original,
                mdx_content=markdown_content,
                page_id=str(page_v1.get('id')) if page_v1 else None,
                input_dir=input_dir,
                output_file_path=args.output_file,
            )
        except Exception as e:
            logging.warning(f"Sidecar mapping 생성 실패 (변환은 성공): {e}")

        # Generate _meta.ts from children.v2.yaml to preserve child order for Netra sidebar
        generate_meta_from_children(input_dir, ctx.OUTPUT_FILE_PATH, PAGES_BY_ID)

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
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
