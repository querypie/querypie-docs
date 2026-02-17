"""Byte-equal 검증 — lossless roundtrip 결과를 page.xhtml과 비교한다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .rehydrator import rehydrate_xhtml
from .sidecar import load_sidecar


@dataclass
class ByteVerificationResult:
    case_id: str
    passed: bool
    reason: str
    first_mismatch_offset: int


def _first_mismatch_offset(a: bytes, b: bytes) -> int:
    limit = min(len(a), len(b))
    for idx in range(limit):
        if a[idx] != b[idx]:
            return idx
    if len(a) != len(b):
        return limit
    return -1


def verify_case_dir(case_dir: Path, sidecar_name: str = "expected.roundtrip.json") -> ByteVerificationResult:
    sidecar_path = case_dir / sidecar_name
    if not sidecar_path.exists():
        return ByteVerificationResult(
            case_id=case_dir.name,
            passed=False,
            reason=f"sidecar_missing:{sidecar_name}",
            first_mismatch_offset=-1,
        )

    expected_mdx = (case_dir / "expected.mdx").read_text(encoding="utf-8")
    page_xhtml = (case_dir / "page.xhtml").read_text(encoding="utf-8")

    sidecar = load_sidecar(sidecar_path)
    generated = rehydrate_xhtml(expected_mdx, sidecar)

    a = page_xhtml.encode("utf-8")
    b = generated.encode("utf-8")
    mismatch = _first_mismatch_offset(a, b)
    if mismatch == -1:
        return ByteVerificationResult(
            case_id=case_dir.name,
            passed=True,
            reason="byte_equal",
            first_mismatch_offset=-1,
        )

    return ByteVerificationResult(
        case_id=case_dir.name,
        passed=False,
        reason="byte_mismatch",
        first_mismatch_offset=mismatch,
    )
