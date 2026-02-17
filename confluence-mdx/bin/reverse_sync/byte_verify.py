"""Byte-equal 검증 — lossless roundtrip 결과를 page.xhtml과 비교한다."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .rehydrator import SpliceResult, rehydrate_xhtml, splice_rehydrate_xhtml
from .sidecar import load_sidecar


@dataclass
class ByteVerificationResult:
    case_id: str
    passed: bool
    reason: str
    first_mismatch_offset: int


@dataclass
class SpliceVerificationResult:
    """Forced-splice 경로 byte-equal 검증 결과."""

    case_id: str
    passed: bool
    reason: str
    first_mismatch_offset: int
    matched_count: int = 0
    emitted_count: int = 0
    total_blocks: int = 0


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


def verify_case_dir_splice(
    case_dir: Path,
    sidecar_name: str = "expected.roundtrip.json",
) -> SpliceVerificationResult:
    """Forced-splice 경로로 byte-equal 검증을 수행한다.

    Document-level fast path를 거치지 않고, 블록 단위 splice 경로만으로
    XHTML을 복원하여 원본과 byte-equal인지 검증한다.
    """
    sidecar_path = case_dir / sidecar_name
    if not sidecar_path.exists():
        return SpliceVerificationResult(
            case_id=case_dir.name,
            passed=False,
            reason=f"sidecar_missing:{sidecar_name}",
            first_mismatch_offset=-1,
        )

    expected_mdx = (case_dir / "expected.mdx").read_text(encoding="utf-8")
    page_xhtml = (case_dir / "page.xhtml").read_text(encoding="utf-8")

    sidecar = load_sidecar(sidecar_path)
    splice_result = splice_rehydrate_xhtml(expected_mdx, sidecar)

    a = page_xhtml.encode("utf-8")
    b = splice_result.xhtml.encode("utf-8")
    mismatch = _first_mismatch_offset(a, b)

    if mismatch == -1:
        return SpliceVerificationResult(
            case_id=case_dir.name,
            passed=True,
            reason="byte_equal_splice",
            first_mismatch_offset=-1,
            matched_count=splice_result.matched_count,
            emitted_count=splice_result.emitted_count,
            total_blocks=splice_result.total_blocks,
        )

    return SpliceVerificationResult(
        case_id=case_dir.name,
        passed=False,
        reason="byte_mismatch_splice",
        first_mismatch_offset=mismatch,
        matched_count=splice_result.matched_count,
        emitted_count=splice_result.emitted_count,
        total_blocks=splice_result.total_blocks,
    )
