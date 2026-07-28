#!/usr/bin/env python3
"""
Batch converter: pages.yaml 기반으로 모든 Confluence page/folder를 MDX로 변환합니다.

translate_titles.py, generate_commands_for_xhtml2markdown.py, xhtml2markdown.ko.sh를
하나의 명령으로 대체합니다.

Usage:
  bin/convert_all.py                       # 전체 변환 (기본: --sync-code qm)
  bin/convert_all.py --sync-code qcp       # QCP Space 변환
  bin/convert_all.py --verify-translations  # 번역 검증만 수행
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence
from urllib.parse import quote, urlsplit

import yaml

# Resolve project root (confluence-mdx/) from this script's location
_SCRIPT_DIR = Path(__file__).resolve().parent        # confluence-mdx/bin/
_PROJECT_DIR = _SCRIPT_DIR.parent                    # confluence-mdx/
_SUPPORTED_CONTENT_TYPES = frozenset({"page", "folder"})
_DEFAULT_CONFLUENCE_BASE_URL = "https://querypie.atlassian.net/wiki"
_MANIFEST_PREFIX = "convert-manifest."
_MANIFEST_SUFFIX = ".yaml"

# Ensure bin/ is on sys.path
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from fetch.sync_profiles import SYNC_PROFILES


def _resolve(rel: str) -> str:
    """Resolve a relative path against _PROJECT_DIR (confluence-mdx/)."""
    p = Path(rel)
    if p.is_absolute():
        return rel
    return str(_PROJECT_DIR / rel)


def load_pages_yaml(pages_yaml_path: str) -> List[Dict]:
    """Load pages.yaml and return typed content entries."""
    with open(pages_yaml_path, 'r', encoding='utf-8') as f:
        pages = yaml.safe_load(f)
    if not isinstance(pages, list):
        raise ValueError(f"pages.yaml should contain a list, got {type(pages)}")
    return pages


def load_translations(translations_file: str) -> Dict[str, str]:
    """Load korean-titles-translations.txt into a dict."""
    translations = {}
    if not os.path.exists(translations_file):
        return translations
    with open(translations_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '|' not in line:
                continue
            parts = line.split('|')
            if len(parts) == 2:
                korean, english = parts[0].strip(), parts[1].strip()
                if korean and english:
                    translations[korean] = english
    return translations


def verify_translations(pages: List[Dict], translations: Dict[str, str]) -> List[Dict]:
    """Check that all Korean titles have translations. Returns list of missing entries."""
    korean_re = re.compile('[가-힣]')
    missing = []
    for page in pages:
        title = page.get('title', '')
        if korean_re.search(title) and title not in translations:
            missing.append(page)
    return missing


class ConversionError(RuntimeError):
    """Raised when a catalog or generated output contract is invalid."""


def _output_relative_path(node: Mapping[str, Any]) -> Path:
    path_parts = node.get("path", [])
    if not isinstance(path_parts, list) or not path_parts:
        raise ConversionError(f"Content {node.get('page_id')} has no valid path")

    normalized_parts = [str(part) for part in path_parts]
    if any(
        not part or part in (".", "..") or Path(part).is_absolute()
        for part in normalized_parts
    ):
        raise ConversionError(
            f"Content {node.get('page_id')} has an unsafe path: {path_parts!r}"
        )
    return Path(*normalized_parts[:-1], f"{normalized_parts[-1]}.mdx")


def _load_yaml_mapping(path: Path, description: str) -> Dict[str, Any]:
    if not path.exists():
        raise ConversionError(f"Missing {description}: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConversionError(f"Invalid YAML in {description} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConversionError(f"{description} must be a mapping: {path}")
    return data


def _child_position(child: Mapping[str, Any]) -> int:
    try:
        return int(child.get("childPosition", 0))
    except (TypeError, ValueError):
        return 0


def _supported_children(
    parent: Mapping[str, Any],
    var_dir: Path,
    nodes_by_id: Mapping[str, Mapping[str, Any]],
) -> List[Mapping[str, Any]]:
    parent_id = str(parent["page_id"])
    data = _load_yaml_mapping(
        var_dir / parent_id / "children.v2.yaml",
        f"direct children snapshot for {parent_id}",
    )
    results = data.get("results", [])
    if not isinstance(results, list):
        raise ConversionError(
            f"children.v2.yaml results must be a list for parent {parent_id}"
        )

    supported: List[Mapping[str, Any]] = []
    for child in sorted(
        (item for item in results if isinstance(item, dict)),
        key=_child_position,
    ):
        child_id_value = child.get("id")
        if child_id_value is None:
            print(
                f"WARNING: skipping malformed child without id parent_id={parent_id}: {child!r}",
                file=sys.stderr,
            )
            continue
        child_id = str(child_id_value)
        catalog_node = nodes_by_id.get(child_id)
        child_type = str(
            child.get("type")
            or (catalog_node or {}).get("type")
            or "page"
        )
        status = str(child.get("status") or "current")
        if status != "current":
            print(
                "WARNING: skipping non-current Confluence child "
                f"parent_id={parent_id} id={child_id} "
                f"type={child_type} status={status} "
                f"title={child.get('title', '')!r}",
                file=sys.stderr,
            )
            continue
        if child_type not in _SUPPORTED_CONTENT_TYPES:
            print(
                "WARNING: skipping unsupported Confluence child "
                f"parent_id={parent_id} id={child_id} "
                f"type={child_type} title={child.get('title', '')!r}",
                file=sys.stderr,
            )
            continue
        if catalog_node is None:
            raise ConversionError(
                f"Supported child {child_id} ({child_type}) of parent {parent_id} "
                "is missing from pages YAML"
            )
        supported.append(catalog_node)
    return supported


def _single_quoted_yaml(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _folder_confluence_url(
    folder_data: Mapping[str, Any],
    base_url: str,
    space_key: str,
    folder_id: str,
) -> str:
    links = folder_data.get("_links", {})
    if not isinstance(links, dict):
        raise ConversionError("folder.v2.yaml _links must be a mapping")
    webui = links.get("webui")

    effective_base = str(links.get("base") or base_url).rstrip("/")
    if not effective_base:
        raise ConversionError("Cannot build folder confluenceUrl without a base URL")
    if not space_key:
        raise ConversionError("Cannot build folder confluenceUrl without a space key")

    if not webui:
        return (
            f"{effective_base}/spaces/{quote(space_key, safe='')}/folder/"
            f"{quote(folder_id, safe='')}"
        )

    webui_str = str(webui)
    if webui_str.startswith(("https://", "http://")):
        return webui_str

    base_parts = urlsplit(effective_base)
    base_path = base_parts.path.rstrip("/")
    if (
        webui_str.startswith("/")
        and base_path
        and (
            webui_str == base_path
            or webui_str.startswith(f"{base_path}/")
        )
    ):
        return f"{base_parts.scheme}://{base_parts.netloc}{webui_str}"
    return f"{effective_base}/{webui_str.lstrip('/')}"


def _markdown_link_title(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def generate_folder_mdx(
    folder: Mapping[str, Any],
    nodes_by_id: Mapping[str, Mapping[str, Any]],
    var_dir: Path,
    output_base_dir: Path,
    base_url: str,
    space_key: str = "QM",
) -> Path:
    """Generate a deterministic folder landing page and return its relative path."""
    folder_id = str(folder["page_id"])
    relative_path = _output_relative_path(folder)
    output_path = output_base_dir / relative_path
    folder_data = _load_yaml_mapping(
        var_dir / folder_id / "folder.v2.yaml",
        f"folder metadata for {folder_id}",
    )
    confluence_url = _folder_confluence_url(
        folder_data,
        base_url,
        space_key,
        folder_id,
    )
    children = _supported_children(folder, var_dir, nodes_by_id)

    title = str(folder.get("title") or folder_data.get("title") or "").strip()
    if not title:
        raise ConversionError(f"Folder {folder_id} has no title")

    lines = [
        "---",
        f"title: {_single_quoted_yaml(title)}",
        f"confluenceUrl: {_single_quoted_yaml(confluence_url)}",
        "---",
        "",
        f"# {title}",
        "",
        "## 하위 문서",
        "",
    ]

    if children:
        for child in children:
            child_relative_path = _output_relative_path(child).with_suffix("")
            link = os.path.relpath(
                child_relative_path,
                start=relative_path.parent,
            ).replace(os.sep, "/")
            if not link.startswith("."):
                link = f"./{link}"
            child_title = _markdown_link_title(str(child.get("title") or ""))
            lines.append(f"- [{child_title}]({link})")
    else:
        lines.append("하위 문서가 없습니다.")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return relative_path


def _typescript_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def generate_navigation(
    pages: Sequence[Mapping[str, Any]],
    var_dir: Path,
    output_base_dir: Path,
) -> List[Dict[str, str]]:
    """Generate non-root navigation files after all MDX outputs exist."""
    if not pages:
        return []

    nodes_by_id = {str(page["page_id"]): page for page in pages}
    root_id = str(pages[0]["page_id"])
    entries: List[Dict[str, str]] = []

    for parent in pages:
        parent_id = str(parent["page_id"])
        if parent_id == root_id:
            continue

        children = _supported_children(parent, var_dir, nodes_by_id)
        if not children:
            continue

        parent_relative_path = _output_relative_path(parent)
        meta_relative_path = parent_relative_path.with_suffix("") / "_meta.ts"
        meta_path = output_base_dir / meta_relative_path
        meta_lines = ["export default {"]

        for child in children:
            child_relative_path = _output_relative_path(child)
            child_output_path = output_base_dir / child_relative_path
            if not child_output_path.is_file():
                raise ConversionError(
                    f"Cannot add child {child['page_id']} to navigation for {parent_id}: "
                    f"missing MDX {child_output_path}"
                )
            slug = _typescript_string(str(child_relative_path.stem))
            title = _typescript_string(str(child.get("title") or ""))
            meta_lines.append(f"  '{slug}': '{title}',")

        meta_lines.extend(["};", ""])
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text("\n".join(meta_lines), encoding="utf-8")
        entries.append({
            "page_id": parent_id,
            "type": str(parent.get("type") or "page"),
            "kind": "navigation",
            "path": meta_relative_path.as_posix(),
        })

    return entries


def _manifest_outputs(path: Path, expected_sync_code: str) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    data = _load_yaml_mapping(path, "conversion manifest")
    manifest_sync_code = data.get("sync_code")
    if manifest_sync_code != expected_sync_code:
        raise ConversionError(
            f"conversion manifest sync_code mismatch: "
            f"expected {expected_sync_code!r}, got {manifest_sync_code!r}"
        )
    outputs = data.get("outputs", [])
    if not isinstance(outputs, list) or not all(
        isinstance(item, dict) for item in outputs
    ):
        raise ConversionError(f"conversion manifest outputs must be a list: {path}")
    return outputs


def _manifest_sync_code(path: Path) -> str:
    name = path.name
    if not name.startswith(_MANIFEST_PREFIX) or not name.endswith(_MANIFEST_SUFFIX):
        raise ConversionError(f"Invalid conversion manifest filename: {path}")
    sync_code = name[len(_MANIFEST_PREFIX):-len(_MANIFEST_SUFFIX)]
    if not sync_code:
        raise ConversionError(f"Missing sync code in conversion manifest: {path}")
    return sync_code


def _catalog_sync_code(path: Path) -> str:
    prefix = "pages."
    suffix = ".yaml"
    name = path.name
    if not name.startswith(prefix) or not name.endswith(suffix):
        raise ConversionError(f"Invalid pages catalog filename: {path}")
    sync_code = name[len(prefix):-len(suffix)]
    if not sync_code:
        raise ConversionError(f"Missing sync code in pages catalog: {path}")
    return sync_code


def _validated_manifest_path(output_root: Path, relative_value: Any) -> Path:
    if not isinstance(relative_value, str):
        raise ConversionError(f"Manifest path must be a string: {relative_value!r}")
    relative_path = Path(relative_value)
    if relative_path.is_absolute():
        raise ConversionError(f"Manifest path must be relative: {relative_value}")

    resolved = (output_root / relative_path).resolve()
    try:
        resolved.relative_to(output_root)
    except ValueError as exc:
        raise ConversionError(
            f"Manifest path escapes output root: {relative_value}"
        ) from exc

    if resolved.suffix != ".mdx" and resolved.name != "_meta.ts":
        raise ConversionError(
            f"Manifest path is not an owned MDX/navigation file: {relative_value}"
        )
    return resolved


def _planned_output_paths(
    pages: Sequence[Mapping[str, Any]],
    var_dir: Path,
) -> set[str]:
    """Calculate all MDX/navigation paths without creating output files."""
    if not pages:
        return set()

    root_id = str(pages[0]["page_id"])
    nodes_by_id = {str(page["page_id"]): page for page in pages}
    planned_paths: set[str] = set()

    for page in pages:
        if str(page["page_id"]) == root_id:
            continue
        content_type = str(page.get("type") or "page")
        if content_type in _SUPPORTED_CONTENT_TYPES:
            planned_paths.add(_output_relative_path(page).as_posix())

    for parent in pages:
        parent_id = str(parent["page_id"])
        if parent_id == root_id:
            continue
        if _supported_children(parent, var_dir, nodes_by_id):
            parent_path = _output_relative_path(parent)
            planned_paths.add(
                (parent_path.with_suffix("") / "_meta.ts").as_posix()
            )

    return planned_paths


def _other_profile_planned_paths(
    manifest_path: Path,
    sync_code: str,
    var_dir: Path,
    output_root: Path,
) -> Dict[str, set[str]]:
    """Load current sibling catalogs, falling back to manifests if absent."""
    manifest_dir = manifest_path.parent
    sibling_codes = {
        _catalog_sync_code(path)
        for path in var_dir.glob("pages.*.yaml")
    }
    sibling_codes.update(
        _manifest_sync_code(path)
        for path in manifest_dir.glob(
            f"{_MANIFEST_PREFIX}*{_MANIFEST_SUFFIX}"
        )
    )
    sibling_codes.discard(sync_code)

    planned_by_profile: Dict[str, set[str]] = {}
    for sibling_code in sorted(sibling_codes):
        catalog_path = var_dir / f"pages.{sibling_code}.yaml"
        if catalog_path.exists():
            sibling_pages = load_pages_yaml(str(catalog_path))
            sibling_paths = _planned_output_paths(sibling_pages, var_dir)
        else:
            sibling_manifest = (
                manifest_dir
                / f"{_MANIFEST_PREFIX}{sibling_code}{_MANIFEST_SUFFIX}"
            )
            sibling_paths = set()
            for entry in _manifest_outputs(
                sibling_manifest,
                sibling_code,
            ):
                relative_path = entry.get("path")
                _validated_manifest_path(output_root, relative_path)
                sibling_paths.add(str(relative_path))

        for relative_path in sibling_paths:
            _validated_manifest_path(output_root, relative_path)
        planned_by_profile[sibling_code] = sibling_paths

    return planned_by_profile


def _ensure_exclusive_output_plan(
    manifest_path: Path,
    sync_code: str,
    pages: Sequence[Mapping[str, Any]],
    var_dir: Path,
    output_root: Path,
) -> None:
    """Reject cross-profile current output collisions before writing files."""
    current_paths = _planned_output_paths(pages, var_dir)
    for relative_path in current_paths:
        _validated_manifest_path(output_root, relative_path)
    for sibling_code, sibling_paths in _other_profile_planned_paths(
        manifest_path,
        sync_code,
        var_dir,
        output_root,
    ).items():
        conflicts = sorted(current_paths & sibling_paths)
        if conflicts:
            conflict_summary = ", ".join(conflicts[:5])
            if len(conflicts) > 5:
                conflict_summary += f", ... ({len(conflicts)} total)"
            raise ConversionError(
                "Current output path collision between sync profiles "
                f"{sync_code!r} and {sibling_code!r}: {conflict_summary}"
            )


def _other_profile_owned_paths(
    manifest_path: Path,
    sync_code: str,
    output_root: Path,
) -> set[str]:
    """Load and validate outputs owned by sibling sync profile manifests."""
    owned_paths: set[str] = set()
    manifest_pattern = f"{_MANIFEST_PREFIX}*{_MANIFEST_SUFFIX}"
    for candidate in sorted(manifest_path.parent.glob(manifest_pattern)):
        if candidate == manifest_path:
            continue
        candidate_sync_code = _manifest_sync_code(candidate)
        if candidate_sync_code == sync_code:
            continue
        for entry in _manifest_outputs(candidate, candidate_sync_code):
            relative_value = entry.get("path")
            _validated_manifest_path(output_root, relative_value)
            owned_paths.add(str(relative_value))
    return owned_paths


def _remove_empty_parents(path: Path, output_root: Path) -> None:
    parent = path.parent
    while parent != output_root:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def finalize_manifest(
    manifest_path: Path,
    sync_code: str,
    current_outputs: Sequence[Mapping[str, str]],
    output_base_dir: Path,
) -> None:
    """Remove exclusively owned stale files and atomically replace the manifest."""
    output_root = output_base_dir.resolve()
    previous_outputs = _manifest_outputs(manifest_path, sync_code)

    previous_by_path: Dict[str, Mapping[str, str]] = {}
    for entry in previous_outputs:
        relative_value = entry.get("path")
        _validated_manifest_path(output_root, relative_value)
        previous_by_path[str(relative_value)] = entry

    current_by_path: Dict[str, Mapping[str, str]] = {}
    for entry in current_outputs:
        relative_value = entry.get("path")
        current_path = _validated_manifest_path(output_root, relative_value)
        if not current_path.is_file():
            raise ConversionError(
                f"Current generated output is missing: {relative_value}"
            )
        current_by_path[str(relative_value)] = entry

    other_profile_paths = _other_profile_owned_paths(
        manifest_path,
        sync_code,
        output_root,
    )
    for stale_relative_path in sorted(
        set(previous_by_path) - set(current_by_path) - other_profile_paths,
        reverse=True,
    ):
        stale_path = _validated_manifest_path(output_root, stale_relative_path)
        if stale_path.exists() or stale_path.is_symlink():
            if not stale_path.is_file() and not stale_path.is_symlink():
                raise ConversionError(
                    f"Refusing to delete non-file manifest path: {stale_relative_path}"
                )
            stale_path.unlink()
            _remove_empty_parents(stale_path, output_root)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_data = {
        "version": 1,
        "sync_code": sync_code,
        "outputs": sorted(current_outputs, key=lambda entry: entry["path"]),
    }
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=manifest_path.parent,
        prefix=f".{manifest_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        yaml.safe_dump(
            manifest_data,
            temp_file,
            allow_unicode=True,
            sort_keys=False,
        )
        temp_path = Path(temp_file.name)
    temp_path.chmod(0o644)
    os.replace(temp_path, manifest_path)


def convert_all(pages: List[Dict], var_dir: str, output_base_dir: str, public_dir: str,
                log_level: str, pages_yaml: str = '',
                manifest_path: str = '', sync_code: str = 'qm',
                base_url: str = _DEFAULT_CONFLUENCE_BASE_URL,
                space_key: str = '') -> int:
    """Convert typed catalog nodes and return the number of failures."""
    # Skip the root page
    root_page_id = pages[0]['page_id'] if pages else None
    targets = [p for p in pages if p['page_id'] != root_page_id]
    nodes_by_id = {str(page["page_id"]): page for page in pages}
    var_path = Path(var_dir)
    output_base_path = Path(output_base_dir)
    profile = SYNC_PROFILES.get(sync_code)
    effective_space_key = space_key or (
        profile.space_key if profile else sync_code.upper()
    )

    total = len(targets)
    failures = 0
    generated_outputs: List[Dict[str, str]] = []

    if manifest_path:
        try:
            _ensure_exclusive_output_plan(
                Path(manifest_path),
                sync_code,
                pages,
                var_path,
                output_base_path.resolve(),
            )
        except Exception as exc:
            print(f"  ERROR: output ownership preflight failed: {exc}", file=sys.stderr)
            return 1

    for i, page in enumerate(targets, 1):
        page_id = str(page['page_id'])
        content_type = str(page.get("type") or "page")
        if content_type not in _SUPPORTED_CONTENT_TYPES:
            print(
                f"[{i}/{total}] SKIP {page_id} (unsupported type {content_type})",
                file=sys.stderr,
            )
            continue

        try:
            relative_path = _output_relative_path(page)
            output_file = output_base_path / relative_path
            if content_type == "folder":
                print(f"[{i}/{total}] {page_id} → {output_file}", file=sys.stderr)
                generate_folder_mdx(
                    page,
                    nodes_by_id,
                    var_path,
                    output_base_path,
                    base_url,
                    effective_space_key,
                )
            else:
                input_file = var_path / page_id / "page.xhtml"
                if not input_file.exists():
                    raise ConversionError(f"Missing page XHTML: {input_file}")

                output_file.parent.mkdir(parents=True, exist_ok=True)
                attachment_dir = Path("/") / relative_path.with_suffix("")
                cmd = [
                    sys.executable, str(_SCRIPT_DIR / 'converter' / 'cli.py'),
                    str(input_file), str(output_file),
                    f'--public-dir={public_dir}',
                    f'--attachment-dir={attachment_dir}',
                    f'--log-level={log_level}',
                ]
                if pages_yaml:
                    cmd.append(f'--pages-yaml={pages_yaml}')

                print(f"[{i}/{total}] {page_id} → {output_file}", file=sys.stderr)
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise ConversionError(result.stderr.strip())

            generated_outputs.append({
                "page_id": page_id,
                "type": content_type,
                "kind": "mdx",
                "path": relative_path.as_posix(),
            })
        except Exception as exc:
            failures += 1
            print(f"  ERROR: {exc}", file=sys.stderr)

    if failures == 0:
        try:
            generated_outputs.extend(
                generate_navigation(pages, var_path, output_base_path)
            )
        except Exception as exc:
            failures += 1
            print(f"  ERROR: navigation generation failed: {exc}", file=sys.stderr)

    if failures == 0 and manifest_path:
        try:
            finalize_manifest(
                Path(manifest_path),
                sync_code,
                generated_outputs,
                output_base_path,
            )
        except Exception as exc:
            failures += 1
            print(f"  ERROR: manifest finalization failed: {exc}", file=sys.stderr)

    return failures


def main():
    parser = argparse.ArgumentParser(
        description='Batch convert Confluence pages and folders to MDX using pages.yaml'
    )
    parser.add_argument('--sync-code', default='qm',
                        help='Sync profile code; used to auto-derive --pages-yaml (default: %(default)s)')
    parser.add_argument('--pages-yaml', default=None,
                        help='Path to pages YAML (default: var/pages.<sync-code>.yaml)')
    parser.add_argument('--var-dir', default='var',
                        help='Directory containing page data (default: var)')
    parser.add_argument('--output-dir', default='target/ko',
                        help='Output directory for MDX files (default: target/ko)')
    parser.add_argument('--public-dir', default='target/public',
                        help='Public assets directory (default: target/public)')
    parser.add_argument('--translations', default='etc/korean-titles-translations.txt',
                        help='Path to translations file')
    parser.add_argument('--base-url', default=_DEFAULT_CONFLUENCE_BASE_URL,
                        help='Confluence base URL for generated folder links')
    parser.add_argument('--space-key', default=None,
                        help='Confluence space key for generated folder links (default: sync profile)')
    parser.add_argument('--verify-translations', action='store_true',
                        help='Verify translation coverage and exit')
    parser.add_argument('--log-level', default='warning',
                        choices=['debug', 'info', 'warning', 'error', 'critical'],
                        help='Log level for converter/cli.py (default: warning)')
    args = parser.parse_args()

    # Auto-derive pages-yaml from sync-code if not explicitly provided
    if args.pages_yaml is None:
        args.pages_yaml = f'var/pages.{args.sync_code}.yaml'

    # Resolve relative paths against project root (confluence-mdx/)
    args.pages_yaml = _resolve(args.pages_yaml)
    args.var_dir = _resolve(args.var_dir)
    args.output_dir = _resolve(args.output_dir)
    args.public_dir = _resolve(args.public_dir)
    args.translations = _resolve(args.translations)
    manifest_path = os.path.join(
        args.var_dir,
        "convert-manifests",
        f"convert-manifest.{args.sync_code}.yaml",
    )
    profile = SYNC_PROFILES.get(args.sync_code)
    space_key = args.space_key or (
        profile.space_key if profile else args.sync_code.upper()
    )

    # Load data
    pages = load_pages_yaml(args.pages_yaml)
    translations = load_translations(args.translations)
    print(f"Loaded {len(pages)} pages, {len(translations)} translations", file=sys.stderr)

    # Verify translations (always run before conversion)
    missing = verify_translations(pages, translations)
    if missing:
        print(f"\nERROR: {len(missing)} Korean titles missing translations:", file=sys.stderr)
        for page in missing:
            print(f"  {page['page_id']}\t{page['title']}", file=sys.stderr)
        print(f"\nAdd translations to {args.translations} and retry.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Translation check passed: all Korean titles covered", file=sys.stderr)

    # --verify-translations: exit after check
    if args.verify_translations:
        sys.exit(0)

    # Run conversions
    failures = convert_all(pages, args.var_dir, args.output_dir, args.public_dir, args.log_level,
                           pages_yaml=args.pages_yaml,
                           manifest_path=manifest_path,
                           sync_code=args.sync_code,
                           base_url=args.base_url,
                           space_key=space_key)

    if failures:
        print(f"\nCompleted with {failures} failure(s) out of {len(pages)} pages", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\nAll pages converted successfully", file=sys.stderr)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
