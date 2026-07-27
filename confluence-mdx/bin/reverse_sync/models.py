"""reverse-sync의 snapshot, manifest, receipt 불변 모델."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any


def sha256_text(value: str) -> str:
    """UTF-8 문자열의 SHA-256을 반환한다."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SyncStatus(str, Enum):
    """reverse-sync 실행 상태."""

    VERIFIED_LOCAL = "verified_local"
    REMOTE_VERIFIED = "remote_verified"
    ALREADY_APPLIED = "already_applied"
    POSTCONDITION_FAILED = "postcondition_failed"


class ReasonCode(str, Enum):
    """자동화가 분기할 수 있는 안정적인 block reason."""

    INVALID_PAGE_SNAPSHOT = "invalid_page_snapshot"
    ARTIFACT_TAMPERED = "artifact_tampered"
    STALE_VERIFICATION = "stale_verification"
    REMOTE_DRIFT = "remote_drift"
    ACTIVE_DRAFT = "active_draft"
    VERSION_CONFLICT = "version_conflict"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_ERROR = "network_error"
    POSTCONDITION_FAILED = "postcondition_failed"


@dataclass(frozen=True)
class PageSnapshot:
    """한 API response에서 획득한 Confluence page의 일관된 상태."""

    page_id: str
    status: str
    title: str
    version: int
    storage_xhtml: str
    fetched_at: str
    api: str

    @property
    def storage_sha256(self) -> str:
        return sha256_text(self.storage_xhtml)

    def to_dict(self, *, include_body: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "api": self.api,
            "fetched_at": self.fetched_at,
            "page_id": self.page_id,
            "status": self.status,
            "storage_sha256": self.storage_sha256,
            "title": self.title,
            "version": self.version,
        }
        if include_body:
            result["storage_xhtml"] = self.storage_xhtml
        return result


@dataclass(frozen=True)
class ArtifactRef:
    """manifest가 참조하는 실행별 artifact."""

    name: str
    path: str
    sha256: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "path": self.path, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ArtifactRef":
        return cls(
            name=str(value["name"]),
            path=str(value["path"]),
            sha256=str(value["sha256"]),
        )


@dataclass(frozen=True)
class VerificationGate:
    """local proof의 개별 gate 결과."""

    name: str
    passed: bool
    reason_code: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"name": self.name, "passed": self.passed}
        if self.reason_code:
            result["reason_code"] = self.reason_code
        return result


@dataclass(frozen=True)
class SyncManifest:
    """verify 결과와 publisher 입력을 hash로 결합하는 immutable 계약."""

    schema_version: int
    run_id: str
    page_id: str
    base_status: str
    base_title: str
    base_version: int
    base_storage_sha256: str
    base_fetched_at: str
    base_api: str
    original_descriptor: str
    improved_descriptor: str
    verifier_policy: str
    tool_version: str
    push_eligible: bool
    artifacts: tuple[ArtifactRef, ...]
    gates: tuple[VerificationGate, ...] = ()

    def artifact(self, name: str) -> ArtifactRef:
        for artifact in self.artifacts:
            if artifact.name == name:
                return artifact
        raise KeyError(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "base": {
                "api": self.base_api,
                "fetched_at": self.base_fetched_at,
                "status": self.base_status,
                "storage_sha256": self.base_storage_sha256,
                "title": self.base_title,
                "version": self.base_version,
            },
            "gates": [gate.to_dict() for gate in self.gates],
            "improved_mdx": {"descriptor": self.improved_descriptor},
            "original_mdx": {"descriptor": self.original_descriptor},
            "page_id": self.page_id,
            "push_eligible": self.push_eligible,
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "tool": {
                "version": self.tool_version,
                "verifier_policy": self.verifier_policy,
            },
        }

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SyncManifest":
        base = value["base"]
        tool = value["tool"]
        return cls(
            schema_version=int(value["schema_version"]),
            run_id=str(value["run_id"]),
            page_id=str(value["page_id"]),
            base_status=str(base["status"]),
            base_title=str(base["title"]),
            base_version=int(base["version"]),
            base_storage_sha256=str(base["storage_sha256"]),
            base_fetched_at=str(base["fetched_at"]),
            base_api=str(base["api"]),
            original_descriptor=str(value["original_mdx"]["descriptor"]),
            improved_descriptor=str(value["improved_mdx"]["descriptor"]),
            verifier_policy=str(tool["verifier_policy"]),
            tool_version=str(tool["version"]),
            push_eligible=bool(value["push_eligible"]),
            artifacts=tuple(
                ArtifactRef.from_dict(item) for item in value.get("artifacts", [])
            ),
            gates=tuple(
                VerificationGate(
                    name=str(item["name"]),
                    passed=bool(item["passed"]),
                    reason_code=str(item.get("reason_code", "")),
                )
                for item in value.get("gates", [])
            ),
        )


@dataclass(frozen=True)
class PushReceipt:
    """manifest를 변경하지 않고 기록하는 remote publish 결과."""

    status: SyncStatus
    page_id: str
    version: int
    title: str
    manifest_sha256: str
    base_version: int
    candidate_sha256: str
    persisted_sha256: str
    response_version: int | None = None
    reason_code: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "base_version": self.base_version,
            "candidate_sha256": self.candidate_sha256,
            "manifest_sha256": self.manifest_sha256,
            "page_id": self.page_id,
            "persisted_sha256": self.persisted_sha256,
            "status": self.status.value,
            "title": self.title,
            "version": self.version,
        }
        if self.response_version is not None:
            result["response_version"] = self.response_version
        if self.reason_code:
            result["reason_code"] = self.reason_code
        return result

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"
