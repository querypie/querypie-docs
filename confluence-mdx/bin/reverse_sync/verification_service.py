"""Reverse Sync candidate 준비와 로컬 검증 lifecycle service."""

from __future__ import annotations

import difflib
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict

import yaml

from mdx_to_storage.parser import parse_mdx_blocks
from reverse_sync.block_diff import diff_blocks
from reverse_sync.equivalence import verify_push_equivalence
from reverse_sync.mapping_recorder import record_mapping
from reverse_sync.planner import plan_patches
from reverse_sync.roundtrip_verifier import verify_roundtrip
from xhtml_beautify_diff import xhtml_diff


@dataclass(frozen=True)
class MdxSource:
    """MDX 파일의 내용과 출처 정보."""

    content: str
    descriptor: str


@dataclass(frozen=True)
class VerificationRuntime:
    """CLI 환경 의존성을 verification lifecycle에 주입합니다."""

    project_dir: Path
    forward_convert: Callable[..., str]
    detect_language: Callable[[str], str]
    planner: Callable[..., Any] = plan_patches
    verifier_policy: str = ""
    tool_version: str = ""


def clean_reverse_sync_artifacts(project_dir: Path, page_id: str) -> Path:
    """이전 reverse-sync 산출물을 정리하고 page별 작업 디렉토리를 반환합니다."""

    var_dir = project_dir / "var" / page_id
    var_dir.mkdir(parents=True, exist_ok=True)
    for artifact in var_dir.glob("reverse-sync.*"):
        if artifact.name == "reverse-sync.backup.xhtml":
            continue
        artifact.unlink()
    verify_mdx = var_dir / "verify.mdx"
    if verify_mdx.exists():
        verify_mdx.unlink()
    verify_dir = var_dir / "verify"
    if verify_dir.exists():
        shutil.rmtree(verify_dir)
    return var_dir


def parse_and_diff(original_mdx: str, improved_mdx: str):
    """MDX 블록을 파싱하고 diff 및 alignment를 반환합니다."""

    original_blocks = parse_mdx_blocks(original_mdx)
    improved_blocks = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original_blocks, improved_blocks)
    return changes, alignment, original_blocks, improved_blocks


def save_diff_yaml(
    var_dir: Path,
    page_id: str,
    now: str,
    original_descriptor: str,
    improved_descriptor: str,
    changes,
) -> None:
    """입력 MDX diff를 page별 진단 산출물로 저장합니다."""

    diff_data = {
        "page_id": page_id,
        "created_at": now,
        "original_mdx": original_descriptor,
        "improved_mdx": improved_descriptor,
        "changes": [
            {
                "index": change.index,
                "block_id": (
                    f"{(change.old_block or change.new_block).type}-{change.index}"
                ),
                "change_type": change.change_type,
                "old_content": (
                    change.old_block.content if change.old_block else None
                ),
                "new_content": (
                    change.new_block.content if change.new_block else None
                ),
            }
            for change in changes
        ],
    }
    (var_dir / "reverse-sync.diff.yaml").write_text(
        yaml.dump(diff_data, allow_unicode=True, default_flow_style=False)
    )


def extract_frontmatter_title(mdx_blocks) -> str:
    """MDX frontmatter에서 title 값을 추출합니다."""

    for block in mdx_blocks:
        if block.type != "frontmatter":
            continue
        for raw_line in block.content.splitlines():
            line = raw_line.strip()
            if not line.startswith("title:"):
                continue
            value = line.split(":", 1)[1].strip()
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {"'", '"'}
            ):
                return value[1:-1]
            return value
    return ""


def compile_result(
    var_dir: Path,
    page_id: str,
    now: str,
    changes_count: int,
    mdx_diff_report: str,
    xhtml_diff_report: str,
    verify_result,
    roundtrip_diff_report: str,
    title: str = "",
    skipped_changes: list | None = None,
) -> Dict[str, Any]:
    """검증 결과를 조립하고 진단 산출물로 저장합니다."""

    status = "pass" if verify_result.passed else "fail"
    result = {
        "page_id": page_id,
        "created_at": now,
        "status": status,
        "push_eligible": False,
        "changes_count": changes_count,
        "mdx_diff_report": mdx_diff_report,
        "xhtml_diff_report": xhtml_diff_report,
        "verification": {
            "exact_match": verify_result.passed,
            "diff_report": roundtrip_diff_report,
        },
    }
    if isinstance(getattr(verify_result, "policy", None), str):
        result["verification"].update(
            policy=verify_result.policy,
            expected_sha256=verify_result.expected_sha256,
            actual_sha256=verify_result.actual_sha256,
        )
    if title:
        result["title"] = title
    if skipped_changes:
        result["skipped_changes"] = skipped_changes
    (var_dir / "reverse-sync.result.yaml").write_text(
        yaml.dump(result, allow_unicode=True, default_flow_style=False)
    )
    return result


def blocked_result(
    var_dir: Path,
    page_id: str,
    now: str,
    reason_code: str,
    *,
    detail: str = "",
) -> Dict[str, Any]:
    """push proof가 fail-closed된 결과를 저장합니다."""

    result = {
        "page_id": page_id,
        "created_at": now,
        "status": "blocked",
        "push_eligible": False,
        "changes_count": 0,
        "reason_code": reason_code,
    }
    if detail:
        result["detail"] = detail
    (var_dir / "reverse-sync.result.yaml").write_text(
        yaml.dump(result, allow_unicode=True, default_flow_style=False)
    )
    return result


def find_blockquotes_missing_blank_line(content: str) -> list:
    """blockquote 다음에 빈 줄이 없는 줄 목록을 반환합니다."""

    lines = content.splitlines()
    in_code_block = False
    violations = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
        if in_code_block:
            continue
        if stripped.startswith(">"):
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            next_stripped = next_line.strip()
            if next_stripped and not next_stripped.startswith(">"):
                violations.append((index + 1, line))
    return violations


def validate_improved_mdx(content: str, descriptor: str) -> None:
    """improved MDX가 deterministic forward conversion 조건을 만족하는지 검증합니다."""

    trailing_ws_lines = [
        (index + 1, line)
        for index, line in enumerate(content.splitlines())
        if line != line.rstrip()
    ]
    if trailing_ws_lines:
        locations = "\n".join(
            f"  line {line_number}: {line!r}"
            for line_number, line in trailing_ws_lines
        )
        raise ValueError(
            f"Trailing whitespace found in improved MDX ({descriptor}).\n"
            "This is an input error, not a reverse-sync bug. "
            "Please remove trailing whitespace before running reverse-sync.\n"
            f"Locations:\n{locations}"
        )

    missing_blank = find_blockquotes_missing_blank_line(content)
    if missing_blank:
        locations = "\n".join(
            f"  line {line_number}: {line!r}"
            for line_number, line in missing_blank
        )
        raise ValueError(
            f"Blockquote not followed by a blank line in improved MDX ({descriptor}).\n"
            "Forward converter always adds a blank line after blockquotes. "
            "Please add a blank line after each blockquote.\n"
            f"Locations:\n{locations}"
        )


def strip_frontmatter(mdx: str) -> str:
    """MDX 문자열에서 YAML frontmatter 블록을 제거합니다."""

    if mdx.startswith("---\n"):
        end = mdx.find("\n---\n", 4)
        if end != -1:
            return mdx[end + 5 :]
    return mdx


def run_verification(
    page_id: str,
    original_src: MdxSource,
    improved_src: MdxSource,
    *,
    runtime: VerificationRuntime,
    xhtml_path: str | None = None,
    lenient: bool = False,
    no_normalize: bool = False,
    language: str | None = None,
    page_dir: str | None = None,
    base_snapshot=None,
    attachment_catalog=None,
    for_push: bool = False,
) -> Dict[str, Any]:
    """candidate 준비부터 local proof/manifest 생성까지 검증 lifecycle을 실행합니다."""

    now = datetime.now(timezone.utc).isoformat()
    var_dir = clean_reverse_sync_artifacts(runtime.project_dir, page_id)

    original_mdx = original_src.content
    improved_mdx = improved_src.content
    dependency_result = None
    link_resolver = None
    attachment_filenames: frozenset[str] = frozenset()

    validate_improved_mdx(improved_mdx, improved_src.descriptor)

    if for_push and base_snapshot is None:
        return blocked_result(
            var_dir,
            page_id,
            now,
            "invalid_page_snapshot",
            detail="online push에는 remote PageSnapshot이 필요합니다.",
        )
    if base_snapshot is not None:
        from reverse_sync.base_parity import (
            load_provenance_storage_xhtml,
            verify_base_parity,
            verify_repository_source_identity,
            verify_source_identity,
        )
        from reverse_sync.dependencies import verify_dependencies

        if base_snapshot.page_id != str(page_id) or base_snapshot.status != "current":
            return blocked_result(
                var_dir,
                page_id,
                now,
                "invalid_page_snapshot",
                detail="snapshot page ID 또는 status가 요청과 다릅니다.",
            )
        pages_path = runtime.project_dir / "var" / "pages.qm.yaml"
        source_identity = verify_repository_source_identity(
            base_snapshot,
            original_mdx,
            improved_mdx,
            original_descriptor=original_src.descriptor,
            improved_descriptor=improved_src.descriptor,
            pages_path=pages_path,
        )
        if not source_identity.passed:
            return blocked_result(
                var_dir,
                page_id,
                now,
                source_identity.reason_code,
                detail=source_identity.diff_report,
            )
        dependency_result, link_resolver = verify_dependencies(
            page_id=page_id,
            original_mdx=original_mdx,
            improved_mdx=improved_mdx,
            pages_path=pages_path,
            attachment_catalog=attachment_catalog,
        )
        if not dependency_result.passed:
            return blocked_result(
                var_dir,
                page_id,
                now,
                dependency_result.reason_code,
                detail=dependency_result.detail,
            )
        attachment_filenames = frozenset(
            requirement.filename
            for requirement in dependency_result.evidence.attachments
        )

        base_xhtml_path = var_dir / "reverse-sync.base.xhtml"
        base_mdx_path = var_dir / "reverse-sync.base.mdx"
        base_xhtml_path.write_text(base_snapshot.storage_xhtml)
        runtime.forward_convert(
            str(base_xhtml_path),
            str(base_mdx_path),
            page_id,
            language=language or runtime.detect_language(improved_src.descriptor),
            page_dir=page_dir,
        )
        converted_base_mdx = base_mdx_path.read_text()
        provenance_dir = (
            Path(page_dir)
            if page_dir
            else runtime.project_dir / "var" / page_id
        )
        base_parity = verify_base_parity(
            base_snapshot,
            original_mdx,
            converted_base_mdx,
            provenance_storage_xhtml=load_provenance_storage_xhtml(
                provenance_dir / "page.v1.yaml",
                expected_page_id=page_id,
            ),
            require_confluence_url=True,
        )
        if not base_parity.passed:
            return blocked_result(
                var_dir,
                page_id,
                now,
                base_parity.reason_code,
                detail=base_parity.diff_report,
            )
        xhtml_path = str(base_xhtml_path)
        xhtml = base_snapshot.storage_xhtml
    else:
        if not xhtml_path:
            xhtml_path = str(
                runtime.project_dir / "var" / page_id / "page.xhtml"
            )
        xhtml = Path(xhtml_path).read_text()

    changes, alignment, original_blocks, improved_blocks = parse_and_diff(
        original_mdx, improved_mdx
    )
    title = extract_frontmatter_title(improved_blocks)
    if not changes:
        result = {
            "page_id": page_id,
            "created_at": now,
            "status": "no_changes",
            "changes_count": 0,
            "push_eligible": False,
            "mdx_diff_report": "",
            "xhtml_diff_report": "",
        }
        if title:
            result["title"] = title
        (var_dir / "reverse-sync.result.yaml").write_text(
            yaml.dump(result, allow_unicode=True, default_flow_style=False)
        )
        return result

    save_diff_yaml(
        var_dir,
        page_id,
        now,
        original_src.descriptor,
        improved_src.descriptor,
        changes,
    )

    from reverse_sync.sidecar import build_sidecar, load_page_lost_info

    page_lost_info = load_page_lost_info(str(var_dir / "mapping.yaml"))
    roundtrip_sidecar = build_sidecar(xhtml, original_mdx, page_id=page_id)
    patch_plan, original_mappings = runtime.planner(
        changes,
        original_blocks,
        improved_blocks,
        page_xhtml=xhtml,
        alignment=alignment,
        page_lost_info=page_lost_info,
        roundtrip_sidecar=roundtrip_sidecar,
        link_resolver=link_resolver,
        attachment_filenames=attachment_filenames,
        allow_text_identity_fallback=not for_push,
        enforce_capabilities=for_push,
        enforce_provenance=for_push,
    )
    skipped_changes = patch_plan.to_legacy_skipped_changes()

    original_mapping_data = {
        "page_id": page_id,
        "created_at": now,
        "source_xhtml": "page.xhtml",
        "blocks": [mapping.__dict__ for mapping in original_mappings],
    }
    (var_dir / "reverse-sync.mapping.original.yaml").write_text(
        yaml.dump(
            original_mapping_data,
            allow_unicode=True,
            default_flow_style=False,
        )
    )
    if for_push:
        from reverse_sync.preserving_patcher import render_patch_plan_preserving

        patched_xhtml = render_patch_plan_preserving(
            xhtml,
            patch_plan,
            roundtrip_sidecar,
        )
    else:
        from reverse_sync.legacy_xhtml_patcher import patch_xhtml

        patched_xhtml = patch_xhtml(xhtml, patch_plan.to_patch_dicts())
    (var_dir / "reverse-sync.patched.xhtml").write_text(patched_xhtml)

    xhtml_diff_report = "\n".join(
        xhtml_diff(
            xhtml,
            patched_xhtml,
            label_a="page.xhtml",
            label_b="reverse-sync.patched.xhtml",
        )
    )

    verify_mapping_data = {
        "page_id": page_id,
        "created_at": now,
        "source_xhtml": "patched.xhtml",
        "blocks": [
            mapping.__dict__ for mapping in record_mapping(patched_xhtml)
        ],
    }
    (var_dir / "reverse-sync.mapping.patched.yaml").write_text(
        yaml.dump(
            verify_mapping_data,
            allow_unicode=True,
            default_flow_style=False,
        )
    )

    src_page_v1 = Path(xhtml_path).parent / "page.v1.yaml"
    dst_page_v1 = var_dir / "page.v1.yaml"
    if src_page_v1.exists() and not dst_page_v1.exists():
        shutil.copy2(src_page_v1, dst_page_v1)

    lang = language or runtime.detect_language(improved_src.descriptor)
    runtime.forward_convert(
        str(var_dir / "reverse-sync.patched.xhtml"),
        str(var_dir / "verify.mdx"),
        page_id,
        language=lang,
        page_dir=page_dir,
    )
    verify_mdx = (var_dir / "verify.mdx").read_text()
    if for_push:
        candidate_identity = verify_source_identity(
            base_snapshot,
            improved_mdx,
            verify_mdx,
            require_confluence_url=True,
        )
        if not candidate_identity.passed:
            return blocked_result(
                var_dir,
                page_id,
                now,
                candidate_identity.reason_code,
                detail=candidate_identity.diff_report,
            )

    orig_stripped = strip_frontmatter(original_mdx)
    impr_stripped = strip_frontmatter(improved_mdx)
    mdx_diff_report = "".join(
        difflib.unified_diff(
            orig_stripped.splitlines(keepends=True),
            impr_stripped.splitlines(keepends=True),
            fromfile=original_src.descriptor,
            tofile=improved_src.descriptor,
            lineterm="",
        )
    )

    verify_stripped = strip_frontmatter(verify_mdx)
    if for_push:
        verify_result = verify_push_equivalence(impr_stripped, verify_stripped)
    else:
        verify_result = verify_roundtrip(
            expected_mdx=impr_stripped,
            actual_mdx=verify_stripped,
            lenient=lenient,
            no_normalize=no_normalize,
        )
    roundtrip_diff_report = "".join(
        difflib.unified_diff(
            impr_stripped.splitlines(keepends=True),
            verify_stripped.splitlines(keepends=True),
            fromfile="improved.mdx",
            tofile="verify.mdx (from patched XHTML)",
            lineterm="",
        )
    )
    result = compile_result(
        var_dir,
        page_id,
        now,
        len(changes),
        mdx_diff_report,
        xhtml_diff_report,
        verify_result,
        roundtrip_diff_report,
        title=title,
        skipped_changes=skipped_changes,
    )

    if for_push:
        result = _finalize_push_verification(
            page_id=page_id,
            original_src=original_src,
            improved_src=improved_src,
            runtime=runtime,
            var_dir=var_dir,
            base_snapshot=base_snapshot,
            dependency_result=dependency_result,
            changes=changes,
            original_blocks=original_blocks,
            improved_blocks=improved_blocks,
            alignment=alignment,
            page_lost_info=page_lost_info,
            roundtrip_sidecar=roundtrip_sidecar,
            link_resolver=link_resolver,
            attachment_filenames=attachment_filenames,
            xhtml=xhtml,
            patched_xhtml=patched_xhtml,
            verify_mdx=verify_mdx,
            impr_stripped=impr_stripped,
            verify_stripped=verify_stripped,
            patch_plan=patch_plan,
            skipped_changes=skipped_changes,
            result=result,
            lenient=lenient,
            no_normalize=no_normalize,
        )

    (var_dir / "reverse-sync.result.yaml").write_text(
        yaml.dump(result, allow_unicode=True, default_flow_style=False)
    )
    return result


def _finalize_push_verification(
    *,
    page_id: str,
    original_src: MdxSource,
    improved_src: MdxSource,
    runtime: VerificationRuntime,
    var_dir: Path,
    base_snapshot,
    dependency_result,
    changes,
    original_blocks,
    improved_blocks,
    alignment,
    page_lost_info,
    roundtrip_sidecar,
    link_resolver,
    attachment_filenames: frozenset[str],
    xhtml: str,
    patched_xhtml: str,
    verify_mdx: str,
    impr_stripped: str,
    verify_stripped: str,
    patch_plan,
    skipped_changes: list,
    result: Dict[str, Any],
    lenient: bool,
    no_normalize: bool,
) -> Dict[str, Any]:
    """push용 deterministic proof와 immutable manifest를 생성합니다."""

    from reverse_sync.manifest import (
        create_sync_manifest,
        update_run_backed_compatibility_outputs,
    )
    from reverse_sync.models import sha256_text
    from reverse_sync.preserving_patcher import render_patch_plan_preserving
    from reverse_sync.proof import build_local_proof
    from reverse_sync.sidecar import build_sidecar

    plan_json = patch_plan.to_canonical_json()
    (var_dir / "reverse-sync.plan.json").write_text(plan_json)

    deterministic_plan, _ = runtime.planner(
        changes,
        original_blocks,
        improved_blocks,
        page_xhtml=xhtml,
        alignment=alignment,
        page_lost_info=page_lost_info,
        roundtrip_sidecar=roundtrip_sidecar,
        link_resolver=link_resolver,
        attachment_filenames=attachment_filenames,
        allow_text_identity_fallback=False,
        enforce_capabilities=True,
        enforce_provenance=True,
    )
    deterministic_plan_json = deterministic_plan.to_canonical_json()
    deterministic_candidate = render_patch_plan_preserving(
        xhtml,
        deterministic_plan,
        roundtrip_sidecar,
    )

    try:
        candidate_sidecar = build_sidecar(
            patched_xhtml,
            verify_mdx,
            page_id=page_id,
        )
        (
            idempotency_changes,
            idempotency_alignment,
            idempotency_original_blocks,
            idempotency_improved_blocks,
        ) = parse_and_diff(verify_mdx, improved_src.content)
        if not idempotency_changes:
            idempotent_candidate = patched_xhtml
        else:
            idempotency_plan, _ = runtime.planner(
                idempotency_changes,
                idempotency_original_blocks,
                idempotency_improved_blocks,
                page_xhtml=patched_xhtml,
                alignment=idempotency_alignment,
                page_lost_info=page_lost_info,
                roundtrip_sidecar=candidate_sidecar,
                link_resolver=link_resolver,
                attachment_filenames=attachment_filenames,
                allow_text_identity_fallback=False,
                enforce_capabilities=True,
                enforce_provenance=True,
            )
            idempotent_candidate = (
                ""
                if idempotency_plan.issues
                else render_patch_plan_preserving(
                    patched_xhtml,
                    idempotency_plan,
                    candidate_sidecar,
                )
            )
    except (ValueError, KeyError):
        idempotent_candidate = ""

    proof = build_local_proof(
        base_xhtml=xhtml,
        improved_mdx=improved_src.content,
        roundtrip_mdx=verify_mdx,
        candidate_xhtml=patched_xhtml,
        sidecar=roundtrip_sidecar,
        changes=changes,
        patches=None,
        skipped_changes=skipped_changes,
        plan_json=plan_json,
        deterministic_plan_json=deterministic_plan_json,
        deterministic_candidate_xhtml=deterministic_candidate,
        idempotent_candidate_xhtml=idempotent_candidate,
        source_identity_passed=True,
        base_parity_passed=True,
        dependency_result=dependency_result,
        plan=patch_plan,
    )
    proof_json = proof.to_canonical_json()
    (var_dir / "reverse-sync.proof.json").write_text(proof_json)

    diagnostics = {}
    if lenient:
        diagnostic = verify_roundtrip(
            expected_mdx=impr_stripped,
            actual_mdx=verify_stripped,
            lenient=True,
        )
        diagnostics["lenient"] = {
            "passed": diagnostic.passed,
            "diff_report": diagnostic.diff_report,
            "push_eligible": False,
        }
    if no_normalize:
        diagnostic = verify_roundtrip(
            expected_mdx=impr_stripped,
            actual_mdx=verify_stripped,
            no_normalize=True,
        )
        diagnostics["raw"] = {
            "passed": diagnostic.passed,
            "diff_report": diagnostic.diff_report,
            "push_eligible": False,
        }

    result.update(
        status=proof.status,
        push_eligible=proof.push_eligible,
        reason_code=proof.blocked_reasons[0] if proof.blocked_reasons else "",
        blocked_reasons=list(proof.blocked_reasons),
        local_gates=[gate.to_dict() for gate in proof.gates],
        verification=proof.equivalence.to_dict(),
    )
    if diagnostics:
        result["diagnostics"] = diagnostics
    if not proof.push_eligible:
        return result

    manifest_path = create_sync_manifest(
        runs_dir=var_dir / "reverse-sync",
        base=base_snapshot,
        original_mdx=original_src.content,
        original_descriptor=original_src.descriptor,
        improved_mdx=improved_src.content,
        improved_descriptor=improved_src.descriptor,
        patch_plan=plan_json,
        candidate_xhtml=patched_xhtml,
        local_proof=proof_json,
        verifier_policy=runtime.verifier_policy,
        tool_version=runtime.tool_version,
        push_eligible=True,
        gates=proof.gates,
    )
    update_run_backed_compatibility_outputs(manifest_path, var_dir)
    result.update(
        push_eligible=True,
        manifest_path=str(manifest_path),
        run_id=manifest_path.parent.name,
        base_version=base_snapshot.version,
        base_storage_sha256=base_snapshot.storage_sha256,
        candidate_sha256=sha256_text(patched_xhtml),
    )
    return result
