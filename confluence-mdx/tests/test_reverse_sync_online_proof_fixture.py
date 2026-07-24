"""실제 converter/golden fixture를 사용하는 online local-proof shadow test."""

from datetime import datetime, timezone
from pathlib import Path

import yaml

from reverse_sync.models import PageSnapshot
from reverse_sync.proof import REQUIRED_LOCAL_GATES
from reverse_sync_cli import MdxSource, run_verify


PROJECT_DIR = Path(__file__).resolve().parent.parent


def test_golden_page_builds_verified_manifest_without_remote_put():
    page_id = "1911652402"
    page_dir = PROJECT_DIR / "tests" / "testcases" / page_id
    original = (page_dir / "original.mdx").read_text()
    improved = (page_dir / "improved.mdx").read_text()
    frontmatter = yaml.safe_load(original.split("---", 2)[1])
    improved = improved.replace(
        "title: 'Reverse Sync Test Page'\n",
        (
            "title: 'Reverse Sync Test Page'\n"
            f"confluenceUrl: '{frontmatter['confluenceUrl']}'\n"
        ),
        1,
    )
    snapshot = PageSnapshot(
        page_id=page_id,
        status="current",
        title=frontmatter["title"],
        version=42,
        storage_xhtml=(page_dir / "page.xhtml").read_text(),
        fetched_at=datetime(2026, 7, 24, tzinfo=timezone.utc).isoformat(),
        api="fixture-shadow",
    )

    result = run_verify(
        page_id=page_id,
        original_src=MdxSource(
            original,
            "main:src/content/ko/unreleased/reverse-sync-test-page.mdx",
        ),
        improved_src=MdxSource(
            improved,
            "src/content/ko/unreleased/reverse-sync-test-page.mdx",
        ),
        page_dir=str(page_dir),
        base_snapshot=snapshot,
        for_push=True,
    )

    assert result["status"] == "verified_local"
    assert result["push_eligible"] is True
    assert tuple(gate["name"] for gate in result["local_gates"]) == (
        REQUIRED_LOCAL_GATES
    )
    assert all(gate["passed"] for gate in result["local_gates"])
    manifest_path = Path(result["manifest_path"])
    assert manifest_path.is_file()
    assert (manifest_path.parent / "patch-plan.json").is_file()
    assert (manifest_path.parent / "local-proof.json").is_file()
