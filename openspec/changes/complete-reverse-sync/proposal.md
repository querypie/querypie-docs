## Why

현재 reverse-sync는 MDX 변경을 기존 Confluence Storage XHTML에 반영하고 forward round-trip으로 검증하는 로컬 파이프라인을 갖추고 있습니다. 2026-07-24 기준 reverse-sync unit test 676개, page fixture 59개, byte-equal fixture 21개가 모두 통과합니다.

그러나 로컬 검증 결과와 실제 Confluence page update 사이에는 안전 계약이 없습니다. 특히 현재 push는 로컬 `page.xhtml`에서 생성한 `reverse-sync.patched.xhtml`을 사용하면서, push 직전에 조회한 원격 최신 version에 `+1`을 적용합니다. 로컬 XHTML이 오래되어도 version conflict가 발생하지 않고 원격 편집을 덮어쓸 수 있습니다.

또한 원본 MDX와 base XHTML의 동등성, 검증 artifact의 무결성, active draft, attachment 참조, push 후 원격 결과를 필수 gate로 확인하지 않습니다. 따라서 현재의 `pass`는 “로컬 round-trip이 통과했다”는 뜻이지 “이 artifact를 현재 원격 page에 안전하게 반영할 수 있다”는 뜻이 아닙니다.

이 change는 reverse-sync를 “변환이 되는 도구”에서 “검증한 snapshot에만 안전하게 반영하고 결과까지 증명하는 workflow”로 완성하기 위한 contract와 구현 순서를 정의합니다.

## What Changes

- Confluence page의 `version`, `title`, Storage XHTML을 하나의 `PageSnapshot`으로 묶고 body hash로 식별합니다.
- original MDX가 base snapshot의 forward conversion 결과와 동등한지 확인하는 base parity gate를 추가합니다.
- MDX 변경 의도, patch 결과, 검증 결과, 입력/출력 hash를 immutable `SyncManifest`에 기록합니다.
- 지원하지 않거나 모호한 변경, skipped change, diagnostic normalization 결과는 push 대상에서 제외합니다.
- push 직전에 원격 snapshot이 검증에 사용한 base와 동일한지 version과 body hash로 재확인합니다.
- version compare-and-set update 후 원격 page를 다시 조회하여 target MDX와의 postcondition을 검증합니다.
- `planner / renderer / proof / publisher` 책임을 분리하고 capability별 지원 범위와 reason code를 표준화합니다.
- 첫 구현 범위에서는 page title 변경, 새 attachment upload, active draft reconciliation을 자동 처리하지 않고 명시적으로 block합니다.
- batch push는 page별 독립 transaction으로 정의하고 부분 성공을 명시적으로 보고합니다.

## Capabilities

### New Capabilities

- `contract-reverse-sync`
  - snapshot-bound MDX → Confluence Storage XHTML 생성
  - base parity 및 immutable manifest
  - fail-closed push eligibility
  - 원격 drift 감지와 compare-and-set update
  - post-write semantic verification 및 recovery evidence

### Modified Capabilities

- 기존 reverse-sync의 `pass / fail / no_changes` 결과를 planning, verification, push eligibility, remote postcondition 상태로 분리합니다.
- 기존 sidecar와 fragment reconstruction을 source snapshot 보존 계층으로 유지하되, text heuristic과 normalization에 의존한 성공 판정을 축소합니다.
- 기존 `reverse_sync_cli.py push`는 verified manifest를 소비하는 publisher로 전환합니다.

## Impact

- 주요 구현 후보
  - `confluence-mdx/bin/reverse_sync_cli.py`
  - `confluence-mdx/bin/reverse_sync/confluence_client.py`
  - `confluence-mdx/bin/reverse_sync/patch_builder.py`
  - `confluence-mdx/bin/reverse_sync/roundtrip_verifier.py`
  - `confluence-mdx/bin/reverse_sync/sidecar.py`
  - 신규 snapshot, manifest, planner, proof, publisher 모듈
- 주요 테스트 후보
  - `confluence-mdx/tests/test_reverse_sync_cli.py`
  - 신규 snapshot/manifest/push transaction contract test
  - `confluence-mdx/tests/test_reverse_sync_*.py`
  - `confluence-mdx/tests/testcases/**`
  - `confluence-mdx/tests/reverse-sync/**`
- 운영 영향
  - stale fetch 또는 base parity 불일치 상태에서는 push가 차단됩니다.
  - 기존 `--lenient`는 진단 용도로만 남고 push eligibility를 부여하지 않습니다.
  - 기존 backup은 유지하되, version/hash가 포함된 실행별 artifact로 대체합니다.
- 관련 자료
  - `confluence-mdx/docs/architecture.md`
  - `confluence-mdx/docs/analysis-reverse-sync-refactoring.md`
  - GitHub issue `#960`
  - [Confluence Cloud REST API v2 Page](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/)
