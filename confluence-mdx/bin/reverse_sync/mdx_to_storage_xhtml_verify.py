"""MDX -> Storage XHTML 검증 유틸리티.

`expected.mdx`를 XHTML fragment로 생성하고 `page.xhtml`과 비교한다.
비교는 BeautifulSoup prettify 기반 정규화를 사용해 포맷 차이를 줄인다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from mdx_to_storage import emit_document, parse_mdx
from xhtml_beautify_diff import beautify_xhtml, xhtml_diff


@dataclass
class CaseVerification:
    case_id: str
    passed: bool
    generated_xhtml: str
    diff_report: str


def mdx_to_storage_xhtml_fragment(mdx_text: str) -> str:
    """MDX 텍스트를 Confluence Storage XHTML fragment로 변환한다."""
    blocks = parse_mdx(mdx_text)
    return emit_document(blocks)


def _normalize_xhtml(xhtml: str) -> str:
    return beautify_xhtml(xhtml).strip()


def verify_expected_mdx_against_page_xhtml(
    expected_mdx: str, page_xhtml: str
) -> tuple[bool, str, str]:
    """expected.mdx로 생성한 XHTML과 page.xhtml을 비교한다."""
    generated = mdx_to_storage_xhtml_fragment(expected_mdx)
    generated_norm = _normalize_xhtml(generated)
    page_norm = _normalize_xhtml(page_xhtml)

    diff_lines = xhtml_diff(
        page_norm,
        generated_norm,
        label_a="page.xhtml",
        label_b="generated-from-expected.mdx.xhtml",
    )
    if not diff_lines:
        return True, generated, ""
    return False, generated, "\n".join(diff_lines)


def iter_testcase_dirs(testcases_dir: Path) -> Iterable[Path]:
    """`page.xhtml`과 `expected.mdx`가 있는 테스트케이스 디렉토리를 순회한다."""
    for child in sorted(testcases_dir.iterdir()):
        if not child.is_dir():
            continue
        if (child / "page.xhtml").exists() and (child / "expected.mdx").exists():
            yield child


def verify_testcase_dir(case_dir: Path) -> CaseVerification:
    """단일 테스트케이스 디렉토리를 검증한다."""
    expected_mdx = (case_dir / "expected.mdx").read_text(encoding="utf-8")
    page_xhtml = (case_dir / "page.xhtml").read_text(encoding="utf-8")
    passed, generated, diff_report = verify_expected_mdx_against_page_xhtml(
        expected_mdx, page_xhtml
    )
    return CaseVerification(
        case_id=case_dir.name,
        passed=passed,
        generated_xhtml=generated,
        diff_report=diff_report,
    )
