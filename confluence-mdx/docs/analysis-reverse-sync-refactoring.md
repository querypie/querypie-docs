# Reverse Sync 현재 구현 상태 분석

이 문서는 2026-04-13 기준 reverse-sync의 실제 구현 상태를 코드베이스, 테스트케이스, 최근 커밋 로그를 바탕으로 다시 정리한 문서입니다.

기존 버전은 2026-02~03 시점의 리팩토링 제안과 phase 계획을 중심으로 작성되어 있었고, `text_transfer.py`, `list_patcher.py`, `table_patcher.py` 같은 과거 설계를 전제로 설명하는 부분이 남아 있었습니다. 현재 구현은 그 이후 다수의 refactor/fix를 거치며 구조가 크게 바뀌었으므로, 이 문서는 "무엇을 해야 하는가"보다 "지금 무엇이 구현되어 있고 어디가 여전히 취약한가"를 설명합니다.

## 1. 한 문장 요약

현재 reverse-sync는 "MDX diff를 XHTML에 보수적으로 반영하고, sidecar 기반 identity preservation과 fragment reconstruction을 활용해 원본 fragment를 최대한 유지하며, 마지막에 forward roundtrip으로 검증하는 시스템"입니다.

즉, 단순 역변환기나 text patcher가 아닙니다.

## 2. 최근 변경 흐름 요약

2026-03-17 이후 reverse-sync 관련 커밋은 대체로 다음 흐름을 보입니다.

1. Phase 5 초기 구현
   - sidecar 타입 기반 매핑
   - heading lookahead 제거
   - reconstruction 경로 도입

2. 구조 재편
   - `text_transfer.py` 제거
   - legacy `list_patcher.py`, `table_patcher.py` 제거
   - `build_patches()` 내부로 매핑/라우팅 책임 집중

3. 회귀 수정 집중
   - preserved anchor list 처리
   - callout 내부 list marker 공백
   - code span 뒤 공백
   - heading 내 badge roundtrip
   - inline boundary whitespace
   - `--no-normalize` 옵션 추가
   - visible segment 모델 도입

이 흐름은 현재 시스템이 아직도 활발히 안정화 중이며, 특히 리스트·인라인 경계·정규화·preserved anchor가 핵심 리스크 영역임을 보여줍니다.

## 3. 현재 아키텍처의 중심축

### 3.1 공개 진입점은 `reverse_sync_cli.py`

CLI 계층은 다음 책임을 맡습니다.

- 단일 파일 verify
- branch 기준 batch verify
- 선택적 push
- 결과 YAML 기록
- failures-only 출력 제어
- `--lenient`, `--no-normalize` 같은 검증 옵션 전달
- push 전 안전장치 및 충돌 처리

하지만 이 파일이 reverse-sync의 "정책 엔진"은 아닙니다.

### 3.2 실제 정책 엔진은 `patch_builder.py`

현재 reverse-sync의 핵심 지능은 `patch_builder.py`에 집중되어 있습니다.

이 모듈이 결정하는 것:

- 어떤 변경을 direct/containing/list/table/paired/skip으로 볼지
- mapping.yaml만으로 처리할지 roundtrip sidecar fallback이 필요한지
- delete/add 쌍을 fragment replacement로 승격할지
- preserved anchor를 rewrite_on_stored_template로 다룰지
- container를 outer wrapper template 기반으로 재구성할지
- table 변경을 허용할지 skip할지
- list 변경을 visible segment 기반으로 흡수할지

현재 설계의 장점은 정책이 한곳에 모여 있다는 점이고, 단점은 정책/예외/skip 분기가 과도하게 집중되어 있다는 점입니다.

### 3.3 sidecar는 lookup 보조가 아니라 identity 계층

현재 구현은 두 종류의 sidecar를 사용합니다.

1. `mapping.yaml`
   - top-level block alignment
   - child alignment
   - `lost_info`
   - 기본 lookup 역인덱스

2. `expected.roundtrip.json` schema v3
   - `xhtml_fragment`
   - `mdx_content_hash`
   - `mdx_line_range`
   - `reconstruction`
   - document envelope / separator

실전에서는 두 번째가 더 중요합니다. 현재 reverse-sync의 안정성은 "이 블록이 어떤 XHTML 요소인가"보다 "이 블록이 원래 어떤 fragment였고 어떤 템플릿으로 재사용할 수 있는가"에 더 크게 의존합니다.

## 4. 현재 구현된 실행 파이프라인

표준 경로는 `run_verify()`로 이해하는 것이 가장 정확합니다.

1. 원본/교정 MDX 로드
2. `parse_mdx_blocks()` + `diff_blocks()`
3. `record_mapping(page.xhtml)`
4. `generate_sidecar_mapping()` 또는 기존 `mapping.yaml` 활용
5. `build_sidecar()`로 roundtrip sidecar v3 생성/활용
6. `build_patches()`로 patch 목록 생성
7. `patch_xhtml()` 적용
8. patched XHTML에서 mapping 재기록
9. patched XHTML을 forward converter로 다시 MDX 변환
10. `verify_roundtrip()`로 improved MDX와 비교
11. pass일 때만 push 후보로 간주

중요한 점은, reverse-sync의 성공 정의가 "patch를 만들었다"가 아니라 "forward roundtrip 증명이 끝났다"는 것입니다.

## 5. 현재 강한 영역

최근 커밋과 테스트 구조를 볼 때 현재 구현이 상대적으로 강한 영역은 다음과 같습니다.

### 5.1 paragraph / heading 중심 교정

- 일반 문단 수정
- heading 텍스트 수정
- badge가 섞인 heading의 roundtrip
- code span / link 주변 공백 보정

### 5.2 sidecar reconstruction이 잘 작동하는 container

- clean container
- 일부 callout / ADF panel
- parameter-bearing container 중 outer wrapper template으로 body만 바꾸는 경로

### 5.3 list의 일부 고질 회귀

최근 수정으로 다음 류의 문제는 이전보다 많이 완화되었습니다.

- marker 뒤 공백 감지
- 선행 공백 축소
- continuation line merge
- preserved anchor list의 item 제거
- callout 내부 list marker 공백

이는 2026-04-13의 visible segment 모델 도입까지 이어진 흐름입니다.

## 6. 현재 취약한 영역

### 6.1 table

테이블은 여전히 가장 조심스럽게 다뤄지는 영역입니다.

현재 구현은 table을 공격적으로 patch하지 않습니다. 위험할 경우 명시적으로 skip합니다.

대표 skip reason:

- `no_mapping`
- `missing_roundtrip_sidecar`
- `preserved_anchor_table`
- `raw_html_table`
- `not_markdown_table`
- `unsafe_html_table_edit`

즉, "table도 어느 정도 된다"가 아니라 "안전한 table만 제한적으로 처리한다"가 현재 상태에 더 가깝습니다.

### 6.2 preserved anchor가 섞인 복합 구조

preserved anchor는 현재 reverse-sync가 원본 XHTML fragment의 정체성을 끝까지 보존하려는 이유를 가장 잘 보여주는 케이스입니다.

- 일반 emitter 재생성으로는 anchor 관련 메타가 쉽게 깨집니다.
- 그래서 rewrite_on_stored_template 또는 sidecar reconstruction으로 우회합니다.
- 하지만 list/table/container가 중첩되면 여전히 리스크가 큽니다.

### 6.3 normalization에 민감한 roundtrip

최근 커밋을 보면 verifier와 converter 정규화가 계속 조정되고 있습니다.

이 말은 곧,

- 실제 patch는 맞지만 verifier에서 mismatch가 날 수 있고
- 반대로 verifier를 느슨하게 하면 실제 회귀를 놓칠 수 있으며
- converter 동작 변화가 reverse-sync pass/fail에 직접 영향을 준다는 뜻입니다.

따라서 reverse-sync는 독립 서브시스템이 아니라 forward converter의 특성에 강하게 결합되어 있습니다.

### 6.4 `patch_builder.py` 단일 집중

현재 구조에서 가장 큰 유지보수 리스크는 `patch_builder.py`에 전략 분기, 예외 처리, sidecar fallback, skip 분류가 과도하게 모여 있다는 점입니다.

이 파일은 현재 기능적으로 중요하지만, 새로운 회귀가 생길 때마다 이곳에 if/elif가 더 쌓이기 쉬운 구조입니다.

## 7. 테스트/픽스처가 보여주는 현재 상태

저장소 기준 확인 가능한 수치는 다음과 같습니다.

- `confluence-mdx/tests/testcases/` 디렉터리: 21개
- 각 testcase에 `page.xhtml`, `expected.mdx`, `expected.roundtrip.json` 존재: 21개
- `original.mdx`, `improved.mdx`, `expected.reverse-sync.patched.xhtml`를 갖춘 reverse-sync fixture: 16개
- `confluence-mdx/tests/reverse-sync/pages.yaml` 항목 수: 67개
- 그중 `failure_type` 메타데이터가 있는 항목: 41개
- `expected_status: pass` 항목: 43개

이 숫자가 의미하는 바는 다음과 같습니다.

1. reverse-sync는 순수 unit test만으로 관리되지 않고, 문서 페이지 fixture 중심의 회귀 방지 체계를 함께 사용합니다.
2. 실패를 "아예 모르는 문제"로 두기보다 `failure_type`, severity, label로 분류하려는 운영 방식이 이미 존재합니다.
3. pages.yaml은 단순 catalog가 아니라 테스트 메타데이터 저장소 역할도 동시에 합니다.

## 8. 기존 문서가 왜 stale해졌는가

기존 문서의 핵심 문제는 "틀린 문제의식"이 아니라 "문제의식은 맞았지만 구현 상태가 바뀌었다"는 데 있습니다.

예를 들어 다음은 여전히 유효한 진단입니다.

- patch_builder가 너무 크다
- 리스트/테이블/인라인 경계가 위험하다
- normalization이 구조적 부담이다
- reverse-sync는 단순 text patching으로 안정화되기 어렵다

반면 다음은 더 이상 현재 상태를 반영하지 않습니다.

- `text_transfer.py` 중심 설명
- `list_patcher.py`, `table_patcher.py`가 여전히 핵심이라는 전제
- roundtrip sidecar를 backward verify 보조 정도로만 보는 설명
- phase 문서의 예정 작업이 아직 미구현이라고 가정하는 표현

즉, 기존 문서를 그대로 읽으면 "아직 해야 할 설계"와 "이미 구현된 설계"가 섞여 보입니다.

## 9. 현재 상태를 문서화할 때의 원칙

현재 문서를 유지보수할 때는 다음 원칙이 필요합니다.

1. 계획과 현황을 분리합니다.
   - 구현 상태 문서는 현재 코드가 실제로 하는 일을 적어야 합니다.
   - 계획 문서는 앞으로 바꿀 설계를 적어야 합니다.

2. `mapping.yaml`과 roundtrip sidecar를 구분해서 설명합니다.
   - 둘은 역할이 다릅니다.

3. 성공 사례보다 보수적 경계를 명시합니다.
   - 어떤 변경은 일부러 skip한다는 점을 숨기면 안 됩니다.

4. reverse-sync를 forward converter와 분리해서 서술하지 않습니다.
   - 최종 성공 판정은 roundtrip에 의존합니다.

5. patch_builder를 "세부 구현"이 아니라 "정책 엔진"으로 설명합니다.

## 10. 결론

현재 reverse-sync는 실패한 실험 단계가 아니라, 이미 상당한 수준의 sidecar/reconstruction 기반 시스템으로 진화한 상태입니다. 다만 그 대가로 다음 특성이 분명해졌습니다.

- 안정성은 올라갔지만 구조는 복잡해졌습니다.
- fragment identity 보존이 핵심이 되었고, 단순 emitter 재생성 전략은 중심에서 밀려났습니다.
- list/table/preserved anchor 같은 영역은 여전히 기능 경계가 뚜렷합니다.
- 향후 개선은 "기능 추가"보다 "정책 분리, 경계 명시, 테스트 피라미드 정리"에 더 가깝게 접근해야 합니다.

이 문서는 현재 구현을 설명하는 기준선입니다. 후속 계획은 별도의 계획 문서에서 다시 정의해야 합니다.
