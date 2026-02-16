# Phase 1 Baseline Verify

## Executed command

```bash
python3 bin/mdx_to_storage_xhtml_verify_cli.py \
  --testcases-dir tests/testcases \
  --show-diff-limit 3
```

## Result

- total: 21
- passed: 0
- failed: 21

## Notes

- Task 1.4/1.5 범위(heading/paragraph/code/list/hr + verify CLI 전환)까지 반영된 기준선 결과다.
- Callout/figure/table/복합 매크로 미지원 항목이 남아 있어, 현재 기준선은 전건 실패다.
