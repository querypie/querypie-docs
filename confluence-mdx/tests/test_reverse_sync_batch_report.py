"""versioned reverse-sync batch report 계약 테스트."""

from reverse_sync.batch_report import BatchReport


def test_partial_success_keeps_page_status_and_nonzero_exit():
    report = BatchReport.from_results(
        command="push",
        branch="proofread/fix",
        results=[
            {
                "file": "src/content/ko/a.mdx",
                "page_id": "1",
                "status": "verified_local",
                "push": {"status": "remote_verified", "version": 6},
            },
            {
                "file": "src/content/ko/b.mdx",
                "page_id": "2",
                "status": "verified_local",
                "push": {
                    "status": "conflict",
                    "reason_code": "version_conflict",
                    "error": "remote changed",
                },
            },
        ],
    )

    value = report.to_dict()

    assert value["kind"] == "reverse-sync-batch-report"
    assert value["schema_version"] == 1
    assert value["outcome"] == "partial_success"
    assert value["exit_code"] == 1
    assert value["summary"]["remote_verified"] == 1
    assert value["summary"]["push_conflict"] == 1
    assert [item["batch_status"] for item in value["results"]] == [
        "remote_verified",
        "push_conflict",
    ]


def test_halted_pages_expose_explicit_resume_manifests():
    report = BatchReport.from_results(
        command="push",
        branch="proofread/fix",
        results=[
            {
                "page_id": "1",
                "status": "verified_local",
                "push": {
                    "status": "postcondition_failed",
                    "reason_code": "postcondition_failed",
                },
            },
            {
                "page_id": "2",
                "status": "verified_local",
                "manifest_path": "/tmp/p2/manifest.json",
                "push": {
                    "status": "not_attempted",
                    "reason_code": "batch_halted_after_postcondition_failure",
                },
            },
        ],
    )

    value = report.to_dict()

    assert value["outcome"] == "failed"
    assert value["summary"]["postcondition_failed"] == 1
    assert value["summary"]["not_attempted"] == 1
    assert value["resume_manifests"] == ["/tmp/p2/manifest.json"]


def test_all_success_has_zero_exit_code():
    report = BatchReport.from_results(
        command="verify",
        branch="proofread/fix",
        results=[
            {"status": "pass"},
            {"status": "no_changes"},
        ],
    )

    value = report.to_dict()

    assert value["outcome"] == "success"
    assert value["exit_code"] == 0
    assert value["summary"]["succeeded"] == 2
    assert value["summary"]["failed"] == 0


def test_user_cancel_is_zero_exit_without_claiming_success():
    report = BatchReport.from_results(
        command="push",
        branch="proofread/fix",
        results=[
            {
                "status": "verified_local",
                "push": {
                    "status": "not_attempted",
                    "reason_code": "user_cancelled",
                },
            }
        ],
    )

    value = report.to_dict()

    assert value["outcome"] == "cancelled"
    assert value["exit_code"] == 0
    assert value["summary"]["cancelled"] == 1
    assert value["summary"]["failed"] == 0


def test_failures_only_filters_results_but_not_summary():
    report = BatchReport.from_results(
        command="push",
        branch="proofread/fix",
        results=[
            {"status": "no_changes"},
            {"status": "blocked", "reason_code": "unsupported_capability"},
        ],
    )

    value = report.to_dict(failures_only=True)

    assert value["summary"]["total"] == 2
    assert len(value["results"]) == 1
    assert value["results"][0]["batch_status"] == "blocked"
