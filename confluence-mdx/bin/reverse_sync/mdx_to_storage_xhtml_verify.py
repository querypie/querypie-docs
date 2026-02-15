"""MDX -> Storage XHTML 검증 유틸리티.

`expected.mdx`를 XHTML fragment로 생성하고 `page.xhtml`과 비교한다.
비교는 BeautifulSoup prettify 기반 정규화를 사용해 포맷 차이를 줄인다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Iterable

from reverse_sync.mdx_block_parser import parse_mdx_blocks
from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_xhtml_element
from xhtml_beautify_diff import beautify_xhtml, xhtml_diff


IGNORED_BLOCK_TYPES = {"frontmatter", "import_statement", "empty"}


@dataclass
class CaseVerification:
    case_id: str
    passed: bool
    generated_xhtml: str
    diff_report: str


def mdx_to_storage_xhtml_fragment(mdx_text: str) -> str:
    """MDX 텍스트를 Confluence Storage XHTML fragment로 변환한다."""
    blocks = parse_mdx_blocks(mdx_text)
    elements: list[str] = []
    for block in blocks:
        if block.type in IGNORED_BLOCK_TYPES:
            continue
        elements.append(mdx_block_to_xhtml_element(block))
    return "".join(elements)


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


def verify_page_vs_generated_with_external_tool(
    page_xhtml_path: Path, generated_xhtml_path: Path
) -> tuple[bool, str]:
    """xhtml_beautify_diff.py를 외부 도구로 실행해 비교한다."""
    script_path = Path(__file__).resolve().parents[1] / "xhtml_beautify_diff.py"
    proc = subprocess.run(
        [str(script_path), str(page_xhtml_path), str(generated_xhtml_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return True, ""
    if proc.returncode == 1:
        return False, proc.stdout.strip()
    raise RuntimeError(
        f"xhtml_beautify_diff failed: code={proc.returncode}, stderr={proc.stderr.strip()}"
    )


def iter_testcase_dirs(testcases_dir: Path) -> Iterable[Path]:
    """`page.xhtml`과 `expected.mdx`가 있는 테스트케이스 디렉토리를 순회한다."""
    for child in sorted(testcases_dir.iterdir()):
        if not child.is_dir():
            continue
        if (child / "page.xhtml").exists() and (child / "expected.mdx").exists():
            yield child


def verify_testcase_dir(
    case_dir: Path,
    *,
    write_generated: bool = False,
    diff_engine: str = "internal",
    generated_filename: str = "generated.from.expected.xhtml",
) -> CaseVerification:
    """단일 테스트케이스 디렉토리를 검증한다."""
    expected_mdx_path = case_dir / "expected.mdx"
    page_xhtml_path = case_dir / "page.xhtml"
    expected_mdx = expected_mdx_path.read_text(encoding="utf-8")
    page_xhtml = page_xhtml_path.read_text(encoding="utf-8")
    generated = mdx_to_storage_xhtml_fragment(expected_mdx)

    generated_path = case_dir / generated_filename
    if write_generated or diff_engine == "external":
        generated_path.write_text(generated, encoding="utf-8")

    if diff_engine == "external":
        passed, diff_report = verify_page_vs_generated_with_external_tool(
            page_xhtml_path, generated_path
        )
    else:
        passed, _gen, diff_report = verify_expected_mdx_against_page_xhtml(
            expected_mdx, page_xhtml
        )
    return CaseVerification(
        case_id=case_dir.name,
        passed=passed,
        generated_xhtml=generated,
        diff_report=diff_report,
    )
