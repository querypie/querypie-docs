# Reverse Sync 디버깅 가이드

## 개요

`reverse_sync_cli.py verify` 실행 시 실패하는 문서를 발견했을 때, 원인을 분석하고 수정하는 디버깅 워크플로우이다.

**소스 코드**: [confluence-mdx/bin/reverse_sync_cli.py](/confluence-mdx/bin/reverse_sync_cli.py)
**관련 Skill**: [reverse-sync.md](reverse-sync.md) — Reverse Sync 기본 사용 가이드

## 사전 준비

### 1. Confluence 원문 최신화

`reverse_sync_cli.py`를 실행하려면 Confluence 원본 XHTML이 로컬에 있어야 한다.

```bash
cd confluence-mdx

# 방법 A: 최근 변경 페이지만 가져오기 (빠름)
bin/fetch_cli.py --recent --attachments

# 방법 B: 전체 페이지를 첨부파일과 함께 가져오기 (완전)
bin/fetch_cli.py --remote --attachments
```

main 브랜치가 최신인지 먼저 확인한다:

```bash
git fetch origin main
git log HEAD..origin/main --oneline   # 뒤처진 커밋이 있는지 확인
```

### 2. 대상 브랜치 준비

디버깅 대상 브랜치를 로컬에 체크아웃하고 remote 변경사항을 반영한다:

```bash
git checkout {branch}
git pull origin {branch}   # remote 변경사항 반영
```

## 검증 실행

```bash
git checkout main   # 검증 명령을 수행하는 것은 main 브랜치에서 수행한다.
cd confluence-mdx
bin/reverse_sync_cli.py verify --branch={branch}
```

### 결과 판정

- **모든 파일이 `pass` 또는 `no_changes`**: 디버깅할 것이 없다. 작업 완료.
- **`fail` 또는 `error`가 있는 경우**: 아래 디버깅 절차를 진행한다.

실패 건만 빠르게 확인하려면:

```bash
bin/reverse_sync_cli.py verify --branch={branch} --failures-only
```

## 용어와 개념

- original.mdx: main 브랜치의 MDX 파일.
  - Confluence 원문의 XHTML 을 Forward Convert 로 변환한 파일이다.
  - 일반적으로, Confluence 원문은 original.mdx 와 동일한 내용을 가진다.
- improved.mdx: 대상 브랜치의 변경된 MDX 파일. 사람 또는 AI Agent 가 변경한 MDX 파일이다.
- verified.mdx: Reverse Sync 를 위해 Round-Trip Verification 과정에서 생성된 MDX 파일이다. 
  - original.mdx 와 improved.mdx 의 차이를 기반으로, Confluence XHTML (page.xhtml) 파일을 변경(Patch)한 후,
    이 patched.xhtml 을 다시 Forward Convert 로 변환한 파일이다.
  - verified.mdx 와 improved.mdx 과 동일하면, verify 에 성공한 것이다.
- Forward Convert:
  - Confluence 원문의 XHTML (page.xhtml)을 Markdown(정확히는 MDX) 형식으로 변환하는 코드의 실행
  - 이 코드는 가능한 XHTML 원문의 구조와 특성을 Markdown 으로 그대로 변환하는 것을 목표로 한다.
  - XHTML 의 컨텐츠, 문구의 오류, 오기, 불필요한 요소를 제거하거나 변경하는 행위를 최소화하는 것을 지향한다.
  - XHTML 컨텐츠, 문구의 오류, 오기, 불필요한 요소가 발견되면, 이것을 교정/교열 과정을 통해 수정하고, Reverse Sync 를 수행하여, Confluence XHTML 원문을 수정하는 것을 지향한다.
- XHTML Patch:
  - original.mdx 와 improved.mdx 의 차이를 기반으로, Confluence XHTML (page.xhtml) 파일을 변경(Patch)하는 코드의 실행
- Reverse Sync:
  - original.mdx 를 수정한 경우, 이 변경사항을 Confluence XHTML 로 변환하고, Confluence 원문에 적용하는 것
  - Reverse Sync 과정의 오류를 방지하기 위해, Round Trip Verification 과정으로 검증한다.
- Round-Trip Verification:
  - improved.mdx 와 verified.mdx 가 동일한지 여부를 검증하는 것
  - Confluence 원문을 변경하지 않고, 원문 변경의 효과를 미리 확인하는 과정이다.
  - XHTML Patch, Forward Convert 과정의 오류를 발견할 수 있다.
- verify 에 실패하는 원인: 다음의 두 가지 사항이 있으며, 이 가운데 XHTML Patch 코드의 버그일 가능성이 높다.
  - XHTML Patch 를 수행하는 코드의 버그
  - Forward Convert 를 수행하는 코드의 버그

## 디버깅 절차

실패하는 문서가 발견된 경우, 다음 절차를 통해 원인을 분석하고 수정한다.

### 1. 실패 문서에 대해 검증 결과 확인하기

실패한 MDX 파일에 대해 단일 파일 단위로 검증 결과를 확인한다.

**verify 모드**: 결과 상태와 불일치 diff를 확인한다.
```bash
bin/reverse_sync_cli.py verify {branch}:{path/to/failed.mdx}
```

**debug 모드**: 세 가지 diff를 상세 출력한다. 원인 분석의 핵심 정보이다.
```bash
bin/reverse_sync_cli.py debug {branch}:{path/to/failed.mdx}
```

debug 모드에서 출력되는 세 가지 diff:
1. **MDX diff** (original.mdx → improved.mdx): 입력 변경 내용
2. **XHTML diff** (page.xhtml → patched.xhtml): XHTML에 적용된 패치
3. **Verify diff** (improved.mdx → verify.mdx): round-trip 불일치 부분 — 이 diff가 실패의 핵심 단서

XHTML 레벨의 변경을 정밀 분석하려면 `xhtml_beautify_diff.py`를 사용한다:
```bash
bin/xhtml_beautify_diff.py \
  var/<page_id>/page.xhtml \
  var/<page_id>/reverse-sync.patched.xhtml
```

중간 산출물은 `var/<page_id>/`에 생성된다:
```
var/<page_id>/
├── reverse-sync.diff.yaml             # MDX 블록 변경 목록
├── reverse-sync.mapping.original.yaml # 원본 XHTML 블록 매핑
├── reverse-sync.patched.xhtml         # 패치된 XHTML
├── reverse-sync.mapping.patched.yaml  # 패치 후 매핑
├── reverse-sync.result.yaml           # 검증 결과 (status, diff 포함)
└── verify.mdx                         # 패치된 XHTML → MDX 재변환 결과
```

### 2. 실패 결과를 재현하는 테스트케이스를 추가하기

테스트케이스를 추가하는 방법은 두 가지이다. 상황에 따라 선택한다.

#### 방법 A: 셸 기반 통합 테스트 (`tests/reverse-sync/`)

페이지 전체의 verify 실패를 그대로 재현하는 방법이다.
실제 XHTML, MDX 파일을 사용하므로 end-to-end 검증에 적합하다.

```bash
cd confluence-mdx/tests

# 1. 테스트케이스 디렉토리 생성 (page_id 사용)
mkdir -p reverse-sync/<page_id>

# 2. 필요한 파일 복사
cp ../var/<page_id>/page.xhtml reverse-sync/<page_id>/page.xhtml
cp ../var/<page_id>/mapping.yaml reverse-sync/<page_id>/mapping.yaml
```

original.mdx와 improved.mdx를 git에서 추출한다:
```bash
# original.mdx: main 브랜치의 MDX 파일
git show main:{path/to/file.mdx} > reverse-sync/<page_id>/original.mdx

# improved.mdx: 대상 브랜치의 변경된 MDX 파일
git show {branch}:{path/to/file.mdx} > reverse-sync/<page_id>/improved.mdx
```

테스트케이스가 실패를 재현하는지 확인한다:
```bash
make test-reverse-sync-bugs-one TEST_ID=<page_id>
```

결과는 `reverse-sync/<page_id>/output.verify.log`에서 확인할 수 있다.

#### 방법 B: Python pytest 단위 테스트

버그가 발생하는 함수를 직접 호출하여 재현하는 방법이다.
원인이 되는 함수를 특정할 수 있을 때 적합하며, 실행이 빠르고 정확한 조건을 통제할 수 있다.

테스트 파일은 `tests/test_reverse_sync_*.py`에 추가한다. 버그가 발생하는 모듈에 대응하는 테스트 파일을 선택한다:

| 버그 위치 | 테스트 파일 |
|-----------|------------|
| `patch_builder.py` (`build_patches`, `build_list_item_patches`) | `test_reverse_sync_patch_builder.py` |
| `text_transfer.py` (`transfer_text_changes`, `find_insert_pos`) | `test_reverse_sync_text_transfer.py` |
| `xhtml_patcher.py` | `test_reverse_sync_xhtml_patcher.py` |
| 기타 모듈 | 대응하는 `test_reverse_sync_*.py` |

테스트 작성 시 기존 헬퍼 함수를 활용한다:
- `_make_mapping()` — XHTML 블록 매핑 fixture 생성
- `_make_change()` — MDX 블록 변경 fixture 생성
- `_make_sidecar()` — sidecar 매핑 fixture 생성

**테스트 작성 패턴** (실제 PR #845, #846, #847 참조):

```python
class TestBugDescription:
    """버그 현상과 재현 시나리오를 클래스 docstring으로 기술한다."""

    def test_specific_failure_case(self):
        """실제 사례의 데이터로 버그를 재현한다.

        재현 시나리오:
          Original MDX: "원래 텍스트"
          Improved MDX: "변경된 텍스트"
          현상: 어떤 오동작이 발생하는지 기술
        """
        # 1. fixture 구성 — 실제 실패 데이터에서 최소한의 재현 데이터를 추출
        mapping = _make_mapping('id', 'xhtml text', xpath='p[1]')
        change = _make_change(0, 'old content', 'new content')
        # ...

        # 2. 버그가 발생하는 함수 호출
        result = build_patches(...)

        # 3. 버그가 재현되는지 assert (수정 전에는 실패해야 함)
        assert '[expected]' in result  # 올바른 동작
        assert not result.startswith('[')  # 버그 동작이 아님을 검증
```

**핵심 원칙:**
- 실제 실패 데이터에서 **최소한의 재현 데이터**를 추출하여 테스트에 사용한다.
- docstring에 **실제 사례**(파일명, 변경 내용)를 기록하여 테스트의 맥락을 보존한다.
- **버그 동작이 아님**을 검증하는 부정 assert를 포함한다 (예: `assert '또한또한' not in result`).
- 수정 전에 테스트를 실행하여 **실패하는 것을 확인**한 후 수정에 착수한다.

테스트 실행:
```bash
cd confluence-mdx/tests
../venv/bin/python3 -m pytest test_reverse_sync_patch_builder.py::TestBugDescription -v
```

### 3. commit 하고 PR 을 생성하기

테스트케이스를 추가한 상태에서 commit 하고 Draft PR을 생성한다.
이 시점에서 테스트는 실패하는 것이 정상이다 (버그 재현 상태).

```bash
# 방법 A의 경우
git add tests/reverse-sync/<page_id>/

# 방법 B의 경우
git add tests/test_reverse_sync_*.py

git commit -m "confluence-mdx: reverse_sync verify 실패 테스트케이스 추가"
```

Draft PR을 생성하여 작업 진행 상황을 공유한다.

### 4. 실패 원인을 분석하고 수정하기

debug 모드의 세 가지 diff와 중간 산출물을 기반으로 원인을 분석한다.

verify 실패의 원인은 두 가지 중 하나이다:
- **XHTML Patch 코드의 버그** (가능성 높음): `bin/reverse_sync/` 아래의 패치 관련 모듈
- **Forward Convert 코드의 버그**: `bin/converter/` 아래의 변환 관련 모듈

**분석 방법:**
1. **Verify diff** (improved.mdx ↔ verify.mdx)를 확인하여 어떤 부분이 다른지 파악한다.
2. **XHTML diff** (page.xhtml ↔ patched.xhtml)를 확인하여 XHTML 패치가 의도대로 적용되었는지 검증한다.
3. patched.xhtml이 잘못되었다면 → XHTML Patch 코드의 버그
4. patched.xhtml은 정상인데 verify.mdx가 다르다면 → Forward Convert 코드의 버그

수정 후 해당 테스트케이스가 통과하는지 확인한다:
```bash
make test-reverse-sync-bugs-one TEST_ID=<page_id>
```

### 5. 로컬 테스트 수행하기

CI 워크플로우 ([`.github/workflows/test-confluence-mdx.yml`](/.github/workflows/test-confluence-mdx.yml))와 동일한 테스트를 모두 수행하여 기존 테스트가 깨지지 않았는지 확인한다.

```bash
cd confluence-mdx/tests

# 1. Python 단위 테스트
../venv/bin/python3 -m pytest -v

# 2. XHTML → MDX 정방향 변환 테스트
make test-convert

# 3. Skeleton MDX 테스트
make test-skeleton

# 4. Reverse-Sync 테스트 (testcases/ 기반)
make test-reverse-sync

# 5. Image-Copy 테스트
make test-image-copy

# 6. XHTML Beautify-Diff 테스트
make test-xhtml-diff

# 7. Byte-equal 라운드트립 검증
make test-byte-verify

# 8. MDX → HTML 렌더링 테스트 (vitest)
make test-render
```

모든 테스트가 통과하면 다음 단계로 진행한다.
실패하는 테스트가 있으면 수정이 기존 동작을 깨뜨린 것이므로, 4단계로 돌아가 수정한다.

### 6. commit 하고 PR 을 업데이트하기

수정 사항을 commit 하고, Draft PR을 Review 가능 상태로 전환한다.

```bash
git add -p   # 변경사항을 확인하며 staging
git commit -m "confluence-mdx: <수정 내용 요약>"
```

PR을 업데이트한다:
- Draft 상태를 해제하여 Review 가능으로 전환한다.
- 최종 commit 을 포함한 상태를 반영하여 PR title과 description을 재작성한다.

### 7. CI 확인 및 완료

PR push 후 CI ([`test-confluence-mdx.yml`](/.github/workflows/test-confluence-mdx.yml)) 실행 결과를 확인한다.

```bash
# PR의 CI check 상태 확인
gh pr checks
```

- **CI 성공**: 디버깅 작업을 성공적으로 종료한다.
- **CI 실패**: 실패한 테스트를 확인하고, 4단계(원인 분석 및 수정) → 5단계(로컬 테스트) → 6단계(commit 및 PR 업데이트)를 반복 수행한다.

## 실제 사례

다음 PR들이 이 디버깅 워크플로우의 실제 사례이다. 모두 Python pytest 단위 테스트(방법 B)로 버그를 재현하고 수정하였다.

| PR | 버그 현상 | 테스트 방법 | 수정 대상 |
|----|-----------|------------|-----------|
| [#845](https://github.com/chequer-io/querypie-docs/pull/845) | push+fetch 후 verify 재실행 시 텍스트 중복 ("또한또한") | `test_reverse_sync_patch_builder.py` — `TestBuildPatchesIdempotency` (2건) | `patch_builder.py` — 멱등성 체크 추가 |
| [#846](https://github.com/chequer-io/querypie-docs/pull/846) | flat list에서 backtick(inline code) 변경이 XHTML 패치에 누락 | `test_reverse_sync_patch_builder.py` — flat list inline code 테스트 (2건) | `patch_builder.py` — inline 마커 감지 + inner XHTML 재생성 |
| [#847](https://github.com/chequer-io/querypie-docs/pull/847) | flat list에서 `[` 삽입 시 XHTML 텍스트 맨 앞에 잘못 배치 | `test_reverse_sync_text_transfer.py` + `test_reverse_sync_patch_builder.py` (3건) | `text_transfer.py` — `find_insert_pos` forward 탐색 추가 |
