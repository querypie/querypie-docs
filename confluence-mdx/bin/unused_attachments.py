#!/usr/bin/env python3
"""
Confluence QM Space 첨부파일 사용 여부 검사 및 삭제 CLI.

각 페이지의 attachments.v1.yaml에서 첨부파일 목록을 수집하고,
page.xhtml 본문에서 ri:attachment 참조를 추출하여 비교합니다.
사용되지 않는 첨부파일을 보고하고, --delete 옵션으로 삭제할 수 있습니다.

Usage:
  bin/unused_attachments.py                     # 미사용 첨부파일 목록 출력
  bin/unused_attachments.py --page-id 1060306945  # 특정 페이지만 검사
  bin/unused_attachments.py --json              # JSON 형식 출력
  bin/unused_attachments.py --delete            # 미사용 첨부파일 삭제 (Confluence API)
"""

import argparse
import json
import logging
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Optional

import yaml

# Resolve project root (confluence-mdx/) from bin/unused_attachments.py
_PROJECT_DIR = Path(__file__).resolve().parent.parent  # confluence-mdx/


def normalize_filename(name: str) -> str:
    """Unicode NFC 정규화로 파일명을 통일합니다."""
    return unicodedata.normalize('NFC', name)


def load_pages_yaml(var_dir: Path) -> list[dict]:
    """var/pages.yaml에서 전체 페이지 목록을 로드합니다."""
    pages_file = var_dir / "pages.yaml"
    if not pages_file.exists():
        return []
    with open(pages_file, encoding='utf-8') as f:
        return yaml.safe_load(f) or []


def load_attachments(page_dir: Path) -> list[dict]:
    """attachments.v1.yaml에서 첨부파일 메타데이터를 로드합니다."""
    att_file = page_dir / "attachments.v1.yaml"
    if not att_file.exists():
        return []
    with open(att_file, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data:
        return []
    return data.get("results", [])


def extract_referenced_filenames(xhtml_content: str) -> set[str]:
    """XHTML 본문에서 ri:attachment ri:filename="..." 참조를 추출합니다.

    ac:image 내부뿐 아니라 모든 ri:attachment 참조를 수집합니다.
    """
    pattern = r'ri:filename="([^"]*)"'
    filenames = set()
    for match in re.finditer(pattern, xhtml_content):
        filenames.add(normalize_filename(match.group(1)))
    return filenames


def scan_all_xhtml_references(var_dir: Path, page_ids: list[str]) -> dict[str, set[str]]:
    """모든 페이지의 XHTML에서 참조된 파일명을 수집합니다.

    Returns:
        dict mapping page_id -> set of referenced filenames (NFC normalized)
    """
    references: dict[str, set[str]] = {}
    for page_id in page_ids:
        xhtml_file = var_dir / page_id / "page.xhtml"
        if not xhtml_file.exists():
            references[page_id] = set()
            continue
        content = xhtml_file.read_text(encoding='utf-8')
        references[page_id] = extract_referenced_filenames(content)
    return references


def build_cross_reference_index(references: dict[str, set[str]],
                                 attachments_by_page: dict[str, list[dict]]) -> dict[str, set[str]]:
    """다른 페이지에서 참조하는 첨부파일을 찾습니다.

    Returns:
        dict mapping "page_id/filename" -> set of page_ids that reference this attachment
    """
    # 페이지별 첨부파일명 집합 구성
    att_names_by_page: dict[str, set[str]] = {}
    for page_id, atts in attachments_by_page.items():
        att_names_by_page[page_id] = {
            normalize_filename(a.get("title", "")) for a in atts
        }

    # 모든 페이지의 XHTML에서 참조된 파일명 중,
    # 해당 페이지가 아닌 다른 페이지의 첨부파일과 이름이 일치하는 것을 탐지
    cross_refs: dict[str, set[str]] = {}
    for ref_page_id, ref_filenames in references.items():
        for owner_page_id, owner_att_names in att_names_by_page.items():
            if owner_page_id == ref_page_id:
                continue
            shared = ref_filenames & owner_att_names
            for filename in shared:
                key = f"{owner_page_id}/{filename}"
                cross_refs.setdefault(key, set()).add(ref_page_id)

    return cross_refs


def find_unused_attachments(var_dir: Path,
                             page_ids: Optional[list[str]] = None,
                             logger: Optional[logging.Logger] = None) -> list[dict]:
    """미사용 첨부파일을 검출합니다.

    Returns:
        list of dicts with keys: page_id, attachment_id, title, file_size, media_type
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # 전체 페이지 목록 결정
    if page_ids is None:
        pages = load_pages_yaml(var_dir)
        all_page_ids = [p["page_id"] for p in pages]
    else:
        all_page_ids = page_ids

    logger.info(f"검사 대상 페이지: {len(all_page_ids)}개")

    # 1) 모든 페이지의 첨부파일 메타데이터 로드
    attachments_by_page: dict[str, list[dict]] = {}
    for page_id in all_page_ids:
        page_dir = var_dir / page_id
        if not page_dir.is_dir():
            continue
        atts = load_attachments(page_dir)
        if atts:
            attachments_by_page[page_id] = atts

    total_attachments = sum(len(v) for v in attachments_by_page.values())
    logger.info(f"전체 첨부파일: {total_attachments}개 ({len(attachments_by_page)}개 페이지)")

    # 2) 모든 페이지의 XHTML 참조 수집
    references = scan_all_xhtml_references(var_dir, all_page_ids)

    # 3) 교차 참조 인덱스 구성
    cross_refs = build_cross_reference_index(references, attachments_by_page)
    if cross_refs:
        logger.info(f"교차 참조 발견: {len(cross_refs)}건")

    # 4) 미사용 첨부파일 검출
    unused: list[dict] = []
    for page_id, atts in attachments_by_page.items():
        page_refs = references.get(page_id, set())
        for att in atts:
            title = normalize_filename(att.get("title", ""))
            att_id = att.get("id", "")
            key = f"{page_id}/{title}"

            # 해당 페이지 XHTML에서 참조되는지 확인
            used_in_own_page = title in page_refs

            # 다른 페이지에서 교차 참조되는지 확인
            cross_ref_pages = cross_refs.get(key, set())

            if not used_in_own_page and not cross_ref_pages:
                extensions = att.get("extensions", {})
                unused.append({
                    "page_id": page_id,
                    "attachment_id": att_id,
                    "title": att.get("title", ""),
                    "file_size": extensions.get("fileSize", 0),
                    "media_type": extensions.get("mediaType", ""),
                })

    logger.info(f"미사용 첨부파일: {len(unused)}개 / 전체 {total_attachments}개")

    return unused


def format_size(size_bytes: int) -> str:
    """파일 크기를 읽기 좋은 형식으로 변환합니다."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def print_report(unused: list[dict], total_attachments: int):
    """미사용 첨부파일 보고서를 출력합니다."""
    if not unused:
        print("미사용 첨부파일이 없습니다.")
        return

    total_size = sum(item.get("file_size", 0) for item in unused)

    print(f"\n미사용 첨부파일: {len(unused)}개 / 전체 {total_attachments}개")
    print(f"절약 가능 용량: {format_size(total_size)}")
    print("=" * 80)

    # 페이지별로 그룹화
    by_page: dict[str, list[dict]] = {}
    for item in unused:
        by_page.setdefault(item["page_id"], []).append(item)

    for page_id in sorted(by_page.keys()):
        items = by_page[page_id]
        page_size = sum(i.get("file_size", 0) for i in items)
        print(f"\n[Page {page_id}] ({len(items)}개, {format_size(page_size)})")
        for item in sorted(items, key=lambda x: x["title"]):
            size_str = format_size(item.get("file_size", 0))
            print(f"  - {item['title']} ({size_str}) [{item['attachment_id']}]")


def delete_attachments(unused: list[dict], config, logger: logging.Logger) -> tuple[int, int]:
    """Confluence API를 통해 미사용 첨부파일을 삭제합니다.

    Returns:
        (success_count, failure_count) tuple
    """
    import requests
    from requests.auth import HTTPBasicAuth

    auth = HTTPBasicAuth(config.email, config.api_token)
    success = 0
    failure = 0

    for item in unused:
        att_id = item["attachment_id"]
        # attachment_id 형식: "att1234567" -> content id는 숫자 부분
        url = f"{config.base_url}/rest/api/content/{att_id}"
        try:
            response = requests.delete(url, auth=auth)
            if response.status_code in (200, 204):
                logger.info(f"삭제 성공: {item['title']} [{att_id}] (page {item['page_id']})")
                success += 1
            else:
                logger.error(f"삭제 실패: {item['title']} [{att_id}] - HTTP {response.status_code}")
                failure += 1
        except Exception as e:
            logger.error(f"삭제 오류: {item['title']} [{att_id}] - {e}")
            failure += 1

    return success, failure


def main():
    parser = argparse.ArgumentParser(
        description="Confluence QM Space 첨부파일 사용 여부 검사 및 삭제"
    )
    parser.add_argument(
        "--var-dir", default=None,
        help="var/ 디렉토리 경로 (기본: confluence-mdx/var)"
    )
    parser.add_argument(
        "--page-id", default=None,
        help="특정 페이지만 검사 (쉼표로 구분하여 여러 개 지정 가능)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="JSON 형식으로 출력"
    )
    parser.add_argument(
        "--delete", action="store_true",
        help="미사용 첨부파일을 Confluence API로 삭제"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="상세 로그 출력"
    )
    args = parser.parse_args()

    # 로깅 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger(__name__)

    # var 디렉토리 결정
    var_dir = Path(args.var_dir) if args.var_dir else _PROJECT_DIR / "var"
    if not var_dir.is_dir():
        logger.error(f"var/ 디렉토리를 찾을 수 없습니다: {var_dir}")
        sys.exit(1)

    # 페이지 ID 필터
    page_ids = None
    if args.page_id:
        page_ids = [pid.strip() for pid in args.page_id.split(",")]

    # 미사용 첨부파일 검출
    unused = find_unused_attachments(var_dir, page_ids, logger)

    # 전체 첨부파일 수 계산 (보고용)
    if page_ids is None:
        pages = load_pages_yaml(var_dir)
        all_page_ids = [p["page_id"] for p in pages]
    else:
        all_page_ids = page_ids
    total_attachments = 0
    for pid in all_page_ids:
        total_attachments += len(load_attachments(var_dir / pid))

    # 출력
    if args.json_output:
        result = {
            "total_attachments": total_attachments,
            "unused_count": len(unused),
            "unused_size_bytes": sum(i.get("file_size", 0) for i in unused),
            "unused": unused,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(unused, total_attachments)

    # 삭제
    if args.delete and unused:
        sys.path.insert(0, str(_PROJECT_DIR / "bin"))
        from reverse_sync.confluence_client import ConfluenceConfig
        config = ConfluenceConfig()
        if not config.email or not config.api_token:
            logger.error("인증 정보를 찾을 수 없습니다. ~/.config/atlassian/confluence.conf를 확인하세요.")
            sys.exit(1)
        print(f"\n{len(unused)}개 첨부파일을 삭제합니다...", file=sys.stderr)
        success, failure = delete_attachments(unused, config, logger)
        print(f"삭제 완료: 성공 {success}개, 실패 {failure}개", file=sys.stderr)
        if failure > 0:
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
