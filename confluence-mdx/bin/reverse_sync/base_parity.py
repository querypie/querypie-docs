"""remote PageSnapshot과 original MDX의 push base parity 검사."""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

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
    match = re.search(r"/pages/(\d+)(?:/|$)", value)
    return match.group(1) if match else ""


def _attachment_filenames_from_mdx(content: str) -> set[str]:
    references = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", content)
    references += re.findall(
        r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']",
        content,
        flags=re.IGNORECASE,
    )
    filenames: set[str] = set()
    for reference in references:
        parsed = urlparse(reference)
        if parsed.scheme in ("http", "https", "data"):
            continue
        filename = PurePosixPath(unquote(parsed.path)).name
        if filename:
            filenames.add(filename)
    return filenames


def verify_attachment_dependencies(
    snapshot: PageSnapshot,
    original_mdx: str,
    improved_mdx: str,
) -> BaseParityResult:
    """improved MDX가 base에 없는 새 attachment를 요구하면 차단한다."""
    original_references = _attachment_filenames_from_mdx(original_mdx)
    improved_references = _attachment_filenames_from_mdx(improved_mdx)
    added_references = improved_references - original_references
    if not added_references:
        return BaseParityResult(True)

    available = set(
        re.findall(
            r"\bri:filename=[\"']([^\"']+)[\"']",
            snapshot.storage_xhtml,
            flags=re.IGNORECASE,
        )
    )
    missing = sorted(added_references - available)
    if missing:
        return BaseParityResult(
            False,
            "missing_attachment",
            "base page에 없는 attachment: " + ", ".join(missing),
        )
    return BaseParityResult(True)


def verify_source_identity(
    snapshot: PageSnapshot,
    original_mdx: str,
    improved_mdx: str,
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

    declared_title = original_title or original_h1
    if declared_title and declared_title != snapshot.title:
        return BaseParityResult(False, "page_identity_mismatch")

    for metadata in (original_meta, improved_meta):
        declared_page_id = _page_id_from_url(metadata.get("confluenceUrl"))
        if declared_page_id and declared_page_id != snapshot.page_id:
            return BaseParityResult(False, "page_identity_mismatch")

    return BaseParityResult(True)


def verify_base_parity(
    snapshot: PageSnapshot,
    original_mdx: str,
    converted_base_mdx: str,
) -> BaseParityResult:
    """forward(base XHTML)과 original MDX content가 동등한지 확인한다."""
    identity = verify_source_identity(snapshot, original_mdx, converted_base_mdx)
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
    return BaseParityResult(False, "base_parity_mismatch", diff)
