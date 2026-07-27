"""reverse-sync가 새로 도입하는 attachment/internal link dependency 검증."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from mdx_to_storage.link_resolver import LinkResolver, load_pages_yaml
from reverse_sync.equivalence import (
    CanonicalDocument,
    InlineToken,
    canonicalize_mdx,
)
from reverse_sync.models import AttachmentCatalog


@dataclass(frozen=True)
class ResolvedLink:
    href: str
    content_title: str
    page_id: str
    anchor: str = ""

    def to_dict(self) -> dict[str, str]:
        value = {
            "content_title": self.content_title,
            "href": self.href,
            "page_id": self.page_id,
        }
        if self.anchor:
            value["anchor"] = self.anchor
        return value


@dataclass(frozen=True)
class AttachmentRequirement:
    filename: str
    attachment_id: str
    version: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "attachment_id": self.attachment_id,
            "filename": self.filename,
            "version": self.version,
        }


@dataclass(frozen=True)
class DependencyEvidence:
    attachments: tuple[AttachmentRequirement, ...] = ()
    internal_links: tuple[ResolvedLink, ...] = ()
    attachment_catalog_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attachment_catalog_sha256": self.attachment_catalog_sha256,
            "attachments": [
                requirement.to_dict()
                for requirement in sorted(
                    self.attachments,
                    key=lambda item: (item.filename, item.attachment_id),
                )
            ],
            "internal_links": [
                link.to_dict()
                for link in sorted(
                    self.internal_links,
                    key=lambda item: (item.href, item.page_id, item.anchor),
                )
            ],
        }


@dataclass(frozen=True)
class DependencyResult:
    passed: bool
    evidence: DependencyEvidence = DependencyEvidence()
    reason_code: str = ""
    detail: str = ""


def _walk_tokens(value: Any) -> Iterable[InlineToken]:
    if isinstance(value, InlineToken):
        yield value
        for child in value.children:
            yield from _walk_tokens(child)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            yield from _walk_tokens(item)


def _document_tokens(document: CanonicalDocument) -> Iterable[InlineToken]:
    for block in document.blocks:
        yield from _walk_tokens(block.tokens)
        yield from _walk_tokens(block.structure)


def _token_text(token: InlineToken) -> str:
    if token.kind in {"text", "code"}:
        return token.value
    if token.kind == "title":
        return ""
    return "".join(_token_text(child) for child in token.children)


def _markdown_references(mdx: str) -> tuple[set[tuple[str, str]], set[str]]:
    links: set[tuple[str, str]] = set()
    images: set[str] = set()
    for token in _document_tokens(canonicalize_mdx(mdx)):
        if token.kind == "link":
            links.add((token.target, _token_text(token)))
        elif token.kind == "image":
            images.add(token.target)

    images.update(
        re.findall(
            r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']",
            mdx,
            flags=re.IGNORECASE,
        )
    )
    for match in re.finditer(
        r"<a\b[^>]*\bhref=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
        mdx,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        links.add(
            (
                match.group(1),
                BeautifulSoup(match.group(2), "html.parser").get_text(),
            )
        )
    return links, images


def _raw_anchor_attributes(
    mdx: str,
) -> set[tuple[str, str, tuple[str, ...]]]:
    anchors: set[tuple[str, str, tuple[str, ...]]] = set()
    for match in re.finditer(
        r"<a\b[^>]*>.*?</a>",
        mdx,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        tag = BeautifulSoup(match.group(0), "html.parser").find("a")
        if tag is None:
            continue
        href = tag.get("href")
        if not isinstance(href, str):
            continue
        extras = tuple(sorted(set(tag.attrs) - {"href"}))
        anchors.add((href, tag.get_text(), extras))
    return anchors


def _is_remote_reference(target: str) -> bool:
    parsed = urlparse(target)
    return bool(parsed.scheme) or target.startswith("//")


def _is_external(target: str) -> bool:
    return _is_remote_reference(target) or target.startswith("#")


def _attachment_filename(target: str) -> str:
    if _is_external(target):
        return ""
    parsed = urlparse(target)
    return PurePosixPath(unquote(parsed.path)).name


def added_attachment_filenames(original_mdx: str, improved_mdx: str) -> tuple[str, ...]:
    """original 대비 새로 참조하는 local attachment filename을 반환합니다."""
    original_links, original_images = _markdown_references(original_mdx)
    improved_links, improved_images = _markdown_references(improved_mdx)
    original_names = {
        filename
        for target in original_images
        if (filename := _attachment_filename(target))
    }
    improved_names = {
        filename
        for target in improved_images
        if (filename := _attachment_filename(target))
    }
    for target, _link_text in original_links:
        if _path_looks_like_attachment(target):
            if filename := _attachment_filename(target):
                original_names.add(filename)
    for target, _link_text in improved_links:
        if _path_looks_like_attachment(target):
            if filename := _attachment_filename(target):
                improved_names.add(filename)
    return tuple(sorted(improved_names - original_names))


def _attachment_requirements(
    filenames: Iterable[str],
    catalog: AttachmentCatalog | None,
) -> tuple[tuple[AttachmentRequirement, ...], DependencyResult | None]:
    required = tuple(sorted(set(filenames)))
    if not required:
        return (), None
    if catalog is None:
        return (), DependencyResult(
            False,
            reason_code="dependency_failure",
            detail=(
                "attachment catalog가 없어 새 attachment reference를 "
                "검증할 수 없습니다"
            ),
        )

    by_filename: dict[str, list[Any]] = {}
    for attachment in catalog.attachments:
        by_filename.setdefault(attachment.filename, []).append(attachment)

    requirements: list[AttachmentRequirement] = []
    for filename in required:
        matches = by_filename.get(filename, [])
        if not matches:
            return (), DependencyResult(
                False,
                reason_code="missing_attachment",
                detail=f"attachment catalog에 없는 filename입니다: {filename}",
            )
        attachment_ids = {match.attachment_id for match in matches}
        if len(matches) != 1 or len(attachment_ids) != 1:
            return (), DependencyResult(
                False,
                reason_code="ambiguous_target",
                detail=f"attachment filename이 여러 identity와 일치합니다: {filename}",
            )
        match = matches[0]
        requirements.append(
            AttachmentRequirement(
                filename=filename,
                attachment_id=match.attachment_id,
                version=match.version,
            )
        )
    return tuple(requirements), None


def _path_looks_like_attachment(target: str) -> bool:
    suffix = PurePosixPath(unquote(urlparse(target).path)).suffix.lower()
    return bool(suffix and suffix != ".mdx")


def verify_dependencies(
    *,
    page_id: str,
    original_mdx: str,
    improved_mdx: str,
    pages_path: Path,
    attachment_catalog: AttachmentCatalog | None,
) -> tuple[DependencyResult, LinkResolver]:
    """새 attachment/link dependency를 catalog로 resolve합니다."""
    pages = load_pages_yaml(pages_path)
    resolver = LinkResolver(pages)
    resolver.set_current_page(str(page_id))
    page_ids = [page.page_id for page in pages]
    if (
        not pages
        or any(not candidate for candidate in page_ids)
        or len(page_ids) != len(set(page_ids))
    ):
        return (
            DependencyResult(
                False,
                reason_code="dependency_failure",
                detail="page catalog의 page identity가 없거나 중복되었습니다",
            ),
            resolver,
        )
    if attachment_catalog is not None and attachment_catalog.page_id != str(page_id):
        return (
            DependencyResult(
                False,
                reason_code="dependency_failure",
                detail="attachment catalog page ID가 target page와 다릅니다",
            ),
            resolver,
        )

    original_links, original_images = _markdown_references(original_mdx)
    improved_links, improved_images = _markdown_references(improved_mdx)
    added_raw_anchors = (
        _raw_anchor_attributes(improved_mdx)
        - _raw_anchor_attributes(original_mdx)
    )
    for href, _link_text, extra_attrs in sorted(added_raw_anchors):
        if not _is_remote_reference(href) and extra_attrs:
            return (
                DependencyResult(
                    False,
                    reason_code="dependency_failure",
                    detail=(
                        "새 internal HTML link의 추가 attribute는 "
                        "지원하지 않습니다: "
                        f"{href} ({', '.join(extra_attrs)})"
                    ),
                ),
                resolver,
            )
    for target in sorted(improved_images - original_images):
        if _is_external(target):
            return (
                DependencyResult(
                    False,
                    reason_code="dependency_failure",
                    detail=(
                        "새 external image reference는 지원하지 않습니다: "
                        f"{target}"
                    ),
                ),
                resolver,
            )
    added_links = sorted(improved_links - original_links)
    attachment_names = set(
        added_attachment_filenames(original_mdx, improved_mdx)
    )
    resolved_links: list[ResolvedLink] = []

    for href, link_text in added_links:
        resolution = resolver.resolve_with_evidence(href, link_text=link_text)
        if resolution.status in {"external", "local_anchor"}:
            continue
        if resolution.status == "resolved":
            resolved_links.append(
                ResolvedLink(
                    href=href,
                    content_title=resolution.content_title or "",
                    page_id=resolution.candidate_page_ids[0],
                    anchor=resolution.anchor or "",
                )
            )
            continue
        filename = _attachment_filename(href)
        if filename and _path_looks_like_attachment(href):
            attachment_names.add(filename)
            continue
        if resolution.status == "ambiguous":
            return (
                DependencyResult(
                    False,
                    reason_code="ambiguous_target",
                    detail=(
                        f"internal link가 여러 page와 일치합니다: {href} "
                        f"({', '.join(resolution.candidate_page_ids)})"
                    ),
                ),
                resolver,
            )
        return (
            DependencyResult(
                False,
                reason_code="internal_link_unresolved",
                detail=f"internal link target을 resolve할 수 없습니다: {href}",
            ),
            resolver,
        )

    requirements, attachment_error = _attachment_requirements(
        attachment_names,
        attachment_catalog,
    )
    if attachment_error is not None:
        return attachment_error, resolver

    evidence = DependencyEvidence(
        attachments=requirements,
        internal_links=tuple(resolved_links),
        attachment_catalog_sha256=(
            attachment_catalog.sha256 if requirements and attachment_catalog else ""
        ),
    )
    return DependencyResult(True, evidence=evidence), resolver
