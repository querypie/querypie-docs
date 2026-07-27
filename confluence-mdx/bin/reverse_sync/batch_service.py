"""Branch 단위 reverse-sync verification/publish state transition service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from reverse_sync.prepare_service import VerificationRequest
from reverse_sync.publish_service import PushConflictError


@dataclass(frozen=True)
class BatchRuntime:
    """CLI, git, 인증, publisher 의존성을 batch lifecycle에 주입합니다."""

    get_changed_files: Callable[[str], List[str]]
    verify_one: Callable[..., dict]
    ensure_config: Callable[[], object]
    publish_one: Callable[..., dict]
    confirm: Callable[[str], bool]
    is_success_status: Callable[[str], bool]
    emit: Callable[..., None]


def run_batch(
    branch: str,
    *,
    runtime: BatchRuntime,
    limit: int = 0,
    failures_only: bool = False,
    push: bool = False,
    yes: bool = False,
    lenient: bool = False,
    no_normalize: bool = False,
    prepare_push: bool = False,
) -> List[dict]:
    """branch 변경 문서를 검증하고 eligible run만 순차 발행합니다."""

    files = runtime.get_changed_files(branch)
    if not files:
        return [{"status": "no_changes", "branch": branch, "changes_count": 0}]

    total = len(files)
    if limit > 0 and not failures_only:
        files = files[:limit]
    count_label = (
        f"up to {total}" if failures_only and limit > 0 else str(len(files))
    )
    runtime.emit(
        f"Processing {count_label}/{total} file(s) from branch {branch}..."
    )

    results = []
    failure_count = 0
    online = push or prepare_push
    config = runtime.ensure_config() if online else None
    for index, ko_path in enumerate(files, 1):
        runtime.emit(
            f"[{index}/{len(files)}] {ko_path} ... ",
            end="",
            flush=True,
        )
        try:
            request = VerificationRequest(
                improved_mdx=f"{branch}:{ko_path}",
                original_mdx=None,
                lenient=lenient,
                no_normalize=no_normalize,
            )
            if online:
                result = runtime.verify_one(
                    request,
                    config=config,
                    prepare_push=True,
                )
            else:
                result = runtime.verify_one(request)
            if online and result.get("status") == "pass":
                result.update(
                    status="blocked",
                    push_eligible=False,
                    reason_code="diagnostic_result_not_pushable",
                )
            result["file"] = ko_path
            runtime.emit(result.get("status", "unknown"))
            results.append(result)
        except Exception as exc:
            runtime.emit("error")
            results.append(
                {
                    "file": ko_path,
                    "status": "error",
                    "error": str(exc),
                }
            )
        if not runtime.is_success_status(
            results[-1].get("status", "unknown")
        ):
            failure_count += 1
        if not push and failures_only and limit > 0 and failure_count >= limit:
            break

    if not push:
        return results

    pushable = [
        result
        for result in results
        if result.get("status") == "verified_local"
        and result.get("push_eligible") is True
    ]
    if not pushable:
        runtime.emit("\nPush 대상 없음 (verified_local 0건)")
        return results

    if not yes:
        runtime.emit(
            f"\n검증 완료: verified_local {len(pushable)}건 / "
            f"전체 {len(results)}건"
        )
        if not runtime.confirm(
            f"{len(pushable)}건을 Confluence에 push 할까요? [y/N] "
        ):
            runtime.emit("Push 취소")
            for result in pushable:
                result["push"] = {
                    "status": "not_attempted",
                    "reason_code": "user_cancelled",
                }
            return results

    push_count = 0
    for push_index, result in enumerate(pushable):
        page_id = result["page_id"]
        try:
            push_result = runtime.publish_one(
                page_id,
                config=config,
                manifest_path=result.get("manifest_path"),
            )
            result["push"] = push_result
            push_count += 1
            runtime.emit(
                f"  pushed {page_id} (v{push_result.get('version', '?')})"
            )
        except PushConflictError as exc:
            result["push"] = {
                "status": "conflict",
                "reason_code": "version_conflict",
                "error": str(exc),
            }
            runtime.emit(f"  conflict {page_id}: {exc}")
        except Exception as exc:
            reason_code = getattr(exc, "reason_code", "") or "push_error"
            if reason_code == "postcondition_failed":
                result["push"] = {
                    "status": "postcondition_failed",
                    "reason_code": reason_code,
                    "error": str(exc),
                }
                for pending in pushable[push_index + 1 :]:
                    pending["push"] = {
                        "status": "not_attempted",
                        "reason_code": (
                            "batch_halted_after_postcondition_failure"
                        ),
                    }
                runtime.emit(f"  postcondition failed {page_id}: {exc}")
                break
            result["push"] = {
                "status": "error",
                "reason_code": reason_code,
                "error": str(exc),
            }
            runtime.emit(f"  error {page_id}: {exc}")

    runtime.emit(f"\nPushed {push_count}/{len(pushable)} file(s)")
    return results
