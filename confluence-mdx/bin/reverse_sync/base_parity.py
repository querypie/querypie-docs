"""remote PageSnapshot과 original MDX의 push base parity 검사."""

from __future__ import annotations

from dataclasses import dataclass
import difflib
from pathlib import Path
import re

import yaml

from reverse_sync.models import PageSnapshot
from reverse_sync.equivalence import verify_push_equivalence


@dataclass(frozen=True)
class BaseParityResult:
    passed: bool
    reason_code: str = ""
    diff_report: str = ""


def _frontmatter(content: str) -> dict:
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---", 4)
    if end < 0:
        return {}
    try:
        value = yaml.safe_load(content[4:end]) or {}
    except yaml.YAMLError:
        return {}
    return value if isinstance(value, dict) else {}


def _first_h1(content: str) -> str:
    fence_char = ""
    fence_length = 0
    for line in content.splitlines():
        fence = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})", line)
        if fence:
            marker = fence.group(1)
            if not fence_char:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = ""
                fence_length = 0
            continue
        if fence_char or line.startswith(("    ", "\t")):
            continue
        match = re.match(r"^# ([^\n]+)$", line)
        if match:
            return match.group(1).strip()
    return ""


def _content_without_frontmatter(content: str) -> str:
    if not content.startswith("---\n"):
        return content
    end = content.find("\n---", 4)
    if end < 0:
        return content
    return content[end + 4 :].lstrip("\n")


def _page_id_from_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    match = re.search(r"/pages/(\d+)(?:[/?#]|$)", value)
    return match.group(1) if match else ""


def verify_source_identity(
    snapshot: PageSnapshot,
    original_mdx: str,
    improved_mdx: str,
    *,
    require_confluence_url: bool = False,
) -> BaseParityResult:
    """title/H1/page URL이 같은 page mutation boundary인지 확인한다."""
    original_meta = _frontmatter(original_mdx)
    improved_meta = _frontmatter(improved_mdx)
    original_title = str(original_meta.get("title", "")).strip()
    improved_title = str(improved_meta.get("title", "")).strip()
    original_h1 = _first_h1(original_mdx)
    improved_h1 = _first_h1(improved_mdx)

    if original_title != improved_title or original_h1 != improved_h1:
        return BaseParityResult(False, "title_change_unsupported")
    if (
        (original_title and original_h1 and original_title != original_h1)
        or (improved_title and improved_h1 and improved_title != improved_h1)
    ):
        return BaseParityResult(
            False,
            "title_change_unsupported",
            "frontmatter title과 첫 H1이 일치하지 않습니다",
        )

    declared_title = original_title or original_h1
    if declared_title and declared_title != snapshot.title:
        return BaseParityResult(False, "page_identity_mismatch")

    for metadata in (original_meta, improved_meta):
        declared_page_id = _page_id_from_url(metadata.get("confluenceUrl"))
        if require_confluence_url and not declared_page_id:
            return BaseParityResult(False, "page_identity_mismatch")
        if declared_page_id and declared_page_id != snapshot.page_id:
            return BaseParityResult(False, "page_identity_mismatch")

    return BaseParityResult(True)


def _repository_path(descriptor: str) -> str:
    value = descriptor.split(":", 1)[-1] if ":" in descriptor else descriptor
    marker = "src/content/ko/"
    if marker not in value or not value.endswith(".mdx"):
        return ""
    return value[value.index(marker) :]


def verify_repository_source_identity(
    snapshot: PageSnapshot,
    original_mdx: str,
    improved_mdx: str,
    *,
    original_descriptor: str,
    improved_descriptor: str,
    pages_path: Path,
) -> BaseParityResult:
    """page ID, confluenceUrl, repository path를 하나의 identity로 검증합니다."""
    content_identity = verify_source_identity(
        snapshot,
        original_mdx,
        improved_mdx,
    )
    if not content_identity.passed:
        return content_identity

    original_path = _repository_path(original_descriptor)
    improved_path = _repository_path(improved_descriptor)
    if not original_path or original_path != improved_path:
        return BaseParityResult(
            False,
            "page_identity_mismatch",
            "original/improved repository MDX path가 없거나 서로 다릅니다",
        )

    try:
        loaded = yaml.safe_load(Path(pages_path).read_text())
    except (OSError, yaml.YAMLError) as exc:
        return BaseParityResult(
            False,
            "page_identity_mismatch",
            f"page catalog를 읽을 수 없습니다: {exc}",
        )
    relative = original_path.removeprefix("src/content/ko/").removesuffix(".mdx")
    expected_parts = relative.split("/")
    rows = loaded if isinstance(loaded, list) else []
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("path") == expected_parts
    ]
    page_id_matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("page_id", "")) == snapshot.page_id
    ]
    if len(matches) != 1 or str(matches[0].get("page_id", "")) != snapshot.page_id:
        return BaseParityResult(
            False,
            "page_identity_mismatch",
            (
                f"repository path {original_path}가 page {snapshot.page_id}와 "
                "유일하게 대응하지 않습니다"
            ),
        )
    if (
        len(page_id_matches) != 1
        or page_id_matches[0].get("path") != expected_parts
    ):
        return BaseParityResult(
            False,
            "page_identity_mismatch",
            (
                f"page {snapshot.page_id}가 repository catalog에서 "
                "유일한 path identity를 갖지 않습니다"
            ),
        )

    for label, content in (
        ("original", original_mdx),
        ("improved", improved_mdx),
    ):
        declared_page_id = _page_id_from_url(
            _frontmatter(content).get("confluenceUrl")
        )
        if not declared_page_id or declared_page_id != snapshot.page_id:
            return BaseParityResult(
                False,
                "page_identity_mismatch",
                (
                    f"{label} MDX confluenceUrl이 page "
                    f"{snapshot.page_id}를 가리키지 않습니다"
                ),
            )
    return BaseParityResult(True)


def load_provenance_storage_xhtml(
    page_v1_path: Path,
    *,
    expected_page_id: str | None = None,
) -> str | None:
    """과거 forward conversion source였던 page.v1 storage body를 읽습니다."""
    try:
        value = yaml.safe_load(Path(page_v1_path).read_text())
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(value, dict) or str(value.get("id", "")) == "":
        return None
    if (
        expected_page_id is not None
        and str(value.get("id")) != str(expected_page_id)
    ):
        return None
    storage = value.get("body", {}).get("storage", {})
    if storage.get("representation") != "storage":
        return None
    xhtml = storage.get("value")
    return xhtml if isinstance(xhtml, str) else None


def verify_base_parity(
    snapshot: PageSnapshot,
    original_mdx: str,
    converted_base_mdx: str,
    *,
    provenance_storage_xhtml: str | None = None,
    require_confluence_url: bool = False,
) -> BaseParityResult:
    """forward(base XHTML)과 original MDX content가 동등한지 확인한다."""
    identity = verify_source_identity(
        snapshot,
        original_mdx,
        converted_base_mdx,
        require_confluence_url=require_confluence_url,
    )
    if not identity.passed:
        return identity

    expected = _content_without_frontmatter(original_mdx)
    actual = _content_without_frontmatter(converted_base_mdx)
    result = verify_push_equivalence(expected, actual)
    if result.passed:
        return BaseParityResult(True)

    diff = result.diff_report or "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="original.mdx",
            tofile="forward(base.xhtml)",
            lineterm="",
        )
    )
    reason_code = "base_parity_mismatch"
    if provenance_storage_xhtml is not None:
        reason_code = (
            "forward_converter_drift"
            if provenance_storage_xhtml == snapshot.storage_xhtml
            else "stale_original_mdx"
        )
    return BaseParityResult(False, reason_code, diff)
