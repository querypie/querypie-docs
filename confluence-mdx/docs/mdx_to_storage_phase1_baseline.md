# Phase 1 Baseline Verify

## Executed command

```bash
python3 bin/mdx_to_storage_xhtml_verify_cli.py --testcases-dir tests/testcases --show-diff-limit 0
```

## Result

- total: 21
- passed: 0
- failed: 21

## Notes

- Task 1.4/1.5 범위(heading/paragraph/code/list/hr + verify CLI 전환) 기준선 결과다.
- Callout/figure/table/복합 매크로 미지원 항목이 남아 있으면 pass 수가 낮을 수 있다.

## Failed Cases

- 1454342158, 1844969501, 1911652402, 544112828, 544113141, 544145591, 544178405, 544211126, 544375741, 544377869, 544379140, 544381877, 544382364, 544384417, 568918170, 692355151, 793608206, 880181257, 883654669, lists, panels
