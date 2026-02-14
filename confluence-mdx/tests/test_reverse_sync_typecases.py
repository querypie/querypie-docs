import difflib
import re
import shutil
from pathlib import Path
import re as _re

import pytest
import yaml

from reverse_sync_cli import MdxSource, run_verify


TESTCASES_ROOT = Path(__file__).parent / "testcases"
TYPECASE_DIRS = sorted([p for p in TESTCASES_ROOT.glob("type-*") if p.is_dir()])
REAL_PAGES_YAML = Path(__file__).parent.parent / "var" / "pages.yaml"


def _strip_fields(text: str, pattern: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not re.search(pattern, line)
    ) + "\n"


def _assert_text_equal(actual: str, expected: str, label_a: str, label_b: str) -> None:
    if actual == expected:
        return
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=label_b,
            tofile=label_a,
            lineterm="",
        )
    )
    raise AssertionError(diff)


def _extract_source_page_id(original_mdx: str) -> str | None:
    m = _re.search(r"/pages/(\d+)/", original_mdx)
    return m.group(1) if m else None


def _load_real_path_map() -> dict[str, list[str]]:
    pages = yaml.safe_load(REAL_PAGES_YAML.read_text()) or []
    out: dict[str, list[str]] = {}
    for p in pages:
        pid = str(p.get("page_id", ""))
        path = p.get("path")
        if pid and isinstance(path, list):
            out[pid] = path
    return out


@pytest.mark.parametrize("case_dir", TYPECASE_DIRS, ids=[p.name for p in TYPECASE_DIRS])
def test_reverse_sync_roundtrip_typecases(case_dir: Path, tmp_path, monkeypatch):
    case_id = case_dir.name
    original_mdx_text = (case_dir / "original.mdx").read_text()
    source_page_id = _extract_source_page_id(original_mdx_text)
    real_paths = _load_real_path_map()
    real_path = real_paths.get(source_page_id or "")
    if not real_path:
        real_path = ["types", case_id]

    # isolated project root for this testcase
    project_dir = tmp_path / "project"
    var_dir = project_dir / "var"
    out_var_case = var_dir / case_id
    out_var_case.mkdir(parents=True, exist_ok=True)

    # minimal pages.yaml so _resolve_attachment_dir() works with non-page-id names
    pages = [{"page_id": case_id, "path": real_path}]
    (var_dir / "pages.yaml").write_text(
        yaml.dump(pages, allow_unicode=True, default_flow_style=False)
    )

    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", project_dir)

    original_path = case_dir / "original.mdx"
    improved_path = case_dir / "improved.mdx"
    xhtml_path = case_dir / "page.xhtml"

    result = run_verify(
        page_id=case_id,
        original_src=MdxSource(
            content=original_mdx_text,
            descriptor=f"tests/testcases/{case_id}/original.mdx",
        ),
        improved_src=MdxSource(
            content=improved_path.read_text(),
            descriptor=f"tests/testcases/{case_id}/improved.mdx",
        ),
        xhtml_path=str(xhtml_path),
    )

    output_dir = tmp_path / "outputs" / case_id
    output_dir.mkdir(parents=True, exist_ok=True)

    out_files = {
        "output.reverse-sync.result.yaml": out_var_case / "reverse-sync.result.yaml",
        "output.reverse-sync.patched.xhtml": out_var_case / "reverse-sync.patched.xhtml",
        "output.reverse-sync.diff.yaml": out_var_case / "reverse-sync.diff.yaml",
        "output.reverse-sync.mapping.original.yaml": out_var_case / "reverse-sync.mapping.original.yaml",
        "output.reverse-sync.mapping.patched.yaml": out_var_case / "reverse-sync.mapping.patched.yaml",
    }
    for out_name, src in out_files.items():
        shutil.copy2(src, output_dir / out_name)

    # original.mdx ↔ improved.mdx diff comparison (run-tests.sh 방식과 동일)
    mdx_diff = "".join(
        difflib.unified_diff(
            original_path.read_text().splitlines(keepends=True),
            improved_path.read_text().splitlines(keepends=True),
            fromfile="a/original.mdx",
            tofile="b/improved.mdx",
            lineterm="",
        )
    )
    (output_dir / "output.mdx.diff").write_text(mdx_diff)
    _assert_text_equal(
        actual=(output_dir / "output.mdx.diff").read_text(),
        expected=(case_dir / "expected.mdx.diff").read_text(),
        label_a=f"{case_id}/output.mdx.diff",
        label_b=f"{case_id}/expected.mdx.diff",
    )

    # expected.reverse-sync.result.yaml (ignore created_at)
    _assert_text_equal(
        actual=_strip_fields(
            (output_dir / "output.reverse-sync.result.yaml").read_text(),
            r"created_at",
        ),
        expected=_strip_fields(
            (case_dir / "expected.reverse-sync.result.yaml").read_text(),
            r"created_at",
        ),
        label_a=f"{case_id}/output.reverse-sync.result.yaml",
        label_b=f"{case_id}/expected.reverse-sync.result.yaml",
    )

    # expected.reverse-sync.patched.xhtml (exact)
    _assert_text_equal(
        actual=(output_dir / "output.reverse-sync.patched.xhtml").read_text(),
        expected=(case_dir / "expected.reverse-sync.patched.xhtml").read_text(),
        label_a=f"{case_id}/output.reverse-sync.patched.xhtml",
        label_b=f"{case_id}/expected.reverse-sync.patched.xhtml",
    )

    # expected.reverse-sync.diff.yaml (ignore created_at, original_mdx, improved_mdx)
    _assert_text_equal(
        actual=_strip_fields(
            (output_dir / "output.reverse-sync.diff.yaml").read_text(),
            r"created_at|original_mdx|improved_mdx",
        ),
        expected=_strip_fields(
            (case_dir / "expected.reverse-sync.diff.yaml").read_text(),
            r"created_at|original_mdx|improved_mdx",
        ),
        label_a=f"{case_id}/output.reverse-sync.diff.yaml",
        label_b=f"{case_id}/expected.reverse-sync.diff.yaml",
    )

    # expected.reverse-sync.mapping.original.yaml (ignore created_at, source_xhtml)
    _assert_text_equal(
        actual=_strip_fields(
            (output_dir / "output.reverse-sync.mapping.original.yaml").read_text(),
            r"created_at|source_xhtml",
        ),
        expected=_strip_fields(
            (case_dir / "expected.reverse-sync.mapping.original.yaml").read_text(),
            r"created_at|source_xhtml",
        ),
        label_a=f"{case_id}/output.reverse-sync.mapping.original.yaml",
        label_b=f"{case_id}/expected.reverse-sync.mapping.original.yaml",
    )

    # expected.reverse-sync.mapping.patched.yaml (ignore created_at, source_xhtml)
    _assert_text_equal(
        actual=_strip_fields(
            (output_dir / "output.reverse-sync.mapping.patched.yaml").read_text(),
            r"created_at|source_xhtml",
        ),
        expected=_strip_fields(
            (case_dir / "expected.reverse-sync.mapping.patched.yaml").read_text(),
            r"created_at|source_xhtml",
        ),
        label_a=f"{case_id}/output.reverse-sync.mapping.patched.yaml",
        label_b=f"{case_id}/expected.reverse-sync.mapping.patched.yaml",
    )

    # sanity checks
    assert result["changes_count"] > 0
    assert (out_var_case / "verify.mdx").exists()
