"""reverse-sync branch batch의 versioned JSON report 계약."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable


BATCH_REPORT_SCHEMA_VERSION = 1
BATCH_REPORT_KIND = "reverse-sync-batch-report"

_SUCCESS_STATUSES = frozenset(
    {
        "already_applied",
        "diagnostic_pass",
        "no_changes",
        "remote_verified",
        "verified_local",
    }
)
_KNOWN_STATUSES = (
    "already_applied",
    "blocked",
    "diagnostic_pass",
    "local_error",
    "local_failed",
    "no_changes",
    "not_attempted",
    "postcondition_failed",
    "push_conflict",
    "push_failed",
    "remote_verified",
    "unknown",
    "verified_local",
)


def _push_status(result: dict[str, Any]) -> str:
    push = result.get("push")
    if not isinstance(push, dict):
        return ""
    status = push.get("status")
    if status in ("remote_verified", "already_applied"):
        return str(status)
    if status == "conflict":
        return "push_conflict"
    if status == "error":
        return "push_failed"
    if status == "postcondition_failed":
        return "postcondition_failed"
    if status == "not_attempted":
        return "not_attempted"
    # 이전 test adapter와의 compatibility boundary입니다. production publisher는
    # 성공 시 항상 remote_verified/already_applied를 반환합니다.
    if status is None and isinstance(push.get("version"), int):
        return "remote_verified"
    return "unknown"


def batch_status(result: dict[str, Any]) -> str:
    """page의 local/publish 상태를 stable batch status로 정규화합니다."""
    publish_status = _push_status(result)
    if publish_status:
        return publish_status
    local_status = result.get("status")
    if local_status == "pass":
        return "diagnostic_pass"
    if local_status in ("verified_local", "no_changes", "blocked"):
        return str(local_status)
    if local_status == "fail":
        return "local_failed"
    if local_status == "error":
        return "local_error"
    return "unknown"


def _reason_code(result: dict[str, Any], status: str) -> str:
    push = result.get("push")
    if isinstance(push, dict):
        reason_code = push.get("reason_code")
        if isinstance(reason_code, str) and reason_code:
            return reason_code
    local_reason = result.get("reason_code")
    if isinstance(local_reason, str) and local_reason:
        return local_reason
    defaults = {
        "local_error": "local_error",
        "local_failed": "local_verification_failed",
        "not_attempted": "not_attempted",
        "postcondition_failed": "postcondition_failed",
        "push_conflict": "version_conflict",
        "push_failed": "push_error",
        "unknown": "unknown",
    }
    return defaults.get(status, "")


def _is_user_cancelled(result: dict[str, Any]) -> bool:
    push = result.get("push")
    return (
        isinstance(push, dict)
        and push.get("status") == "not_attempted"
        and push.get("reason_code") == "user_cancelled"
    )


@dataclass(frozen=True)
class BatchReport:
    """page별 결과와 process outcome을 함께 직렬화하는 immutable view."""

    command: str
    branch: str
    results: tuple[dict[str, Any], ...]

    @classmethod
    def from_results(
        cls,
        *,
        command: str,
        branch: str,
        results: Iterable[dict[str, Any]],
    ) -> "BatchReport":
        if command not in ("verify", "push", "debug"):
            raise ValueError(f"지원하지 않는 batch command입니다: {command}")
        return cls(command=command, branch=branch, results=tuple(results))

    @property
    def statuses(self) -> tuple[str, ...]:
        return tuple(batch_status(result) for result in self.results)

    @property
    def outcome(self) -> str:
        if self.results and all(
            status in _SUCCESS_STATUSES or _is_user_cancelled(result)
            for result, status in zip(self.results, self.statuses)
        ) and any(_is_user_cancelled(result) for result in self.results):
            return "cancelled"

        succeeded = sum(status in _SUCCESS_STATUSES for status in self.statuses)
        failed = len(self.statuses) - succeeded
        if failed == 0:
            return "success"
        if succeeded:
            return "partial_success"
        return "failed"

    @property
    def exit_code(self) -> int:
        return 0 if self.outcome in ("success", "cancelled") else 1

    def _result_view(self, result: dict[str, Any]) -> dict[str, Any]:
        status = batch_status(result)
        view = dict(result)
        view["batch_status"] = status
        reason_code = _reason_code(result, status)
        if reason_code:
            view["reason_code"] = reason_code
        return view

    def to_dict(self, *, failures_only: bool = False) -> dict[str, Any]:
        statuses = self.statuses
        counts = Counter(statuses)
        cancelled = sum(_is_user_cancelled(result) for result in self.results)
        succeeded = sum(status in _SUCCESS_STATUSES for status in statuses)
        failed = len(statuses) - succeeded - cancelled
        summary = {
            "total": len(statuses),
            "succeeded": succeeded,
            "failed": failed,
            "cancelled": cancelled,
            **{status: counts[status] for status in _KNOWN_STATUSES},
        }
        result_views = [
            self._result_view(result)
            for result in self.results
            if not failures_only or batch_status(result) not in _SUCCESS_STATUSES
        ]
        resume_manifests = sorted(
            {
                str(result["manifest_path"])
                for result in self.results
                if batch_status(result) == "not_attempted"
                and isinstance(result.get("push"), dict)
                and result["push"].get("reason_code")
                == "batch_halted_after_postcondition_failure"
                and result.get("manifest_path")
            }
        )
        return {
            "branch": self.branch,
            "command": self.command,
            "exit_code": self.exit_code,
            "kind": BATCH_REPORT_KIND,
            "outcome": self.outcome,
            "results": result_views,
            "resume_manifests": resume_manifests,
            "schema_version": BATCH_REPORT_SCHEMA_VERSION,
            "summary": summary,
        }
