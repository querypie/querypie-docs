# 중복 코드 분석 및 리팩토링 범위

> 작성일: 2026-02-17
> 대상: `confluence-mdx/` 아래 reverse-sync, mdx-to-storage, converter 등 전체 모듈

## 1. 분석 개요

confluence-mdx 코드베이스에서 중복 및 유사 구현을 탐색하여 리팩토링 범위를 정의합니다.
모듈 간 동일/유사 로직이 독립적으로 구현된 경우를 식별하고, 공통 모듈 추출 방안을 제시합니다.

### 모듈 구조 개요

```
bin/
├── converter/          # Forward: XHTML → MDX (2,498줄)
├── mdx_to_storage/     # Backward: MDX → XHTML (1,139줄)
├── reverse_sync/       # 변경 감지 & 패칭 (2,929줄)
├── fetch/              # Confluence API (1,149줄)
├── skeleton/           # 구조 추출 (2,364줄)
└── (CLI 스크립트들)
```

## 2. 중복 코드 상세 분석

---

### 2.1 [완료] MDX 블록 파서 중복

**중복 파일:**
- `reverse_sync/mdx_block_parser.py` (129줄) — `MdxBlock` 데이터클래스, `parse_mdx_blocks()`
- `mdx_to_storage/parser.py` (473줄) — `Block` 데이터클래스, `parse_mdx()`

**데이터 모델 중복:**

```python
# reverse_sync/mdx_block_parser.py:6-12
@dataclass
class MdxBlock:
    type: str       # heading, paragraph, code_block, list, html, ...
    content: str
    line_start: int
    line_end: int

# mdx_to_storage/parser.py:16-25
@dataclass
class Block:
    type: str       # heading, paragraph, code_block, list, callout, ...
    content: str
    level: int = 0
    language: str = ''
    children: list = field(default_factory=list)
    attrs: dict = field(default_factory=dict)
```

**파싱 로직 중복:**

| 기능 | mdx_block_parser.py | parser.py | 유사도 |
|------|---------------------|-----------|--------|
| 리스트 감지 `_is_list_line()` | 110-120줄 | 414-420줄 | **동일 로직** |
| 리스트 연속 `_is_list_continuation()` | 122-129줄 | 422-425줄 | **동일 로직** |
| 코드 블록 파싱 | 46-55줄 | 165-177줄 | 유사 접근 |
| Heading 감지 | 58-61줄 (`line.startswith('#')`) | 156-162줄 (regex `_HEADING_PATTERN`) | 유사 |
| Frontmatter 파싱 | 29-38줄 | 119-138줄 | 유사 (parser.py가 더 상세) |
| HTML 블록 감지 | 62-72줄 | 242-310줄 | 유사 (parser.py가 더 상세) |
| 빈 줄 처리 | 40-44줄 | 47-50줄 | 동일 |

**리팩토링 방안:**

1. **통합 파서 모듈 생성:** `bin/mdx_parser/` 또는 `bin/shared/mdx_parser.py`
2. **통합 데이터 모델:** `Block` 기반으로 통합 (더 풍부한 속성 보유)
   - `MdxBlock`의 `line_start`, `line_end`를 `Block`에 추가
   - 파싱 모드 옵션으로 경량/상세 선택 가능하게 구현
3. **공통 헬퍼 추출:** `_is_list_line()`, `_is_list_continuation()` 등을 공유 모듈로 이동

**예상 절감:** ~80줄 (mdx_block_parser.py의 대부분을 parser.py로 통합)

**실행 결과:** `parser.py`의 `Block`에 `line_start`/`line_end` 필드를 추가하고, `parse_mdx_blocks()` 호환 함수를 추가했습니다. `mdx_block_parser.py`는 backward-compat re-export 래퍼로 전환했습니다. 8개 파일의 import 경로를 업데이트했습니다.

---

### 2.2 [완료] 인라인 변환기 중복

**중복 파일:**
- `reverse_sync/mdx_to_xhtml_inline.py` (270줄) — LinkResolver 통합, heading 전용 처리
- `mdx_to_storage/inline.py` (94줄) — 경량 인라인 변환

**코드 스팬 추출/복원 중복:**

```python
# mdx_to_storage/inline.py:28-30
code_spans = []
def _save(m):
    code_spans.append(m.group(0))
    return f"\x00CODE{len(code_spans)-1}\x00"

# reverse_sync/mdx_to_xhtml_inline.py:28-30
code_spans = []
def _save(m):
    code_spans.append(m.group(0))
    return f"\x00CODE{len(code_spans)-1}\x00"
```

**Bold/Italic 변환 중복:**

```python
# mdx_to_storage/inline.py:34-35
text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)

# reverse_sync/mdx_to_xhtml_inline.py:33-35
text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
```

**코드 스팬 복원 중복:**

```python
# 두 파일 모두 동일한 복원 로직
text = re.sub(r'\x00CODE(\d+)\x00', lambda m: ..., text)
```

**차이점:**
- `mdx_to_xhtml_inline.py`는 `***bold italic***` 패턴을 추가로 처리
- `mdx_to_xhtml_inline.py`는 `convert_heading_inline()` 제공 (bold 마커 사전 제거)
- `mdx_to_xhtml_inline.py`는 `LinkResolver` 통합
- `mdx_to_xhtml_inline.py`는 `mdx_block_to_xhtml_element()` 블록 레벨 변환 포함

**리팩토링 방안:**

1. **기반 모듈:** `mdx_to_storage/inline.py`를 기반으로 확장
2. **확장 모듈:** `reverse_sync/mdx_to_xhtml_inline.py`는 기반을 import하고 추가 기능만 구현
3. **공유 로직:** 코드 스팬 추출/복원, bold/italic regex를 공통 모듈로 추출

**예상 절감:** ~50줄

**실행 결과:** `mdx_to_xhtml_inline.py`의 자체 `_convert_inline()`을 삭제하고 `mdx_to_storage.inline.convert_inline`을 import하여 사용하도록 변경했습니다. 블록 레벨 함수(`mdx_block_to_inner_xhtml()`, `mdx_block_to_xhtml_element()`)는 유지합니다.

---

### 2.3 [완료] 텍스트 정규화 유틸리티 중복

**중복 파일:**
- `reverse_sync/text_normalizer.py` (97줄)
- `bin/text_utils.py` (81줄)
- `converter/context.py` (일부 함수)

**중복 상세:**

| 기능 | text_utils.py | text_normalizer.py | context.py |
|------|---------------|-------------------|------------|
| 텍스트 정리 | `clean_text()` :23-41 | — | import from text_utils |
| 공백 축약 | — | `collapse_ws()` :89-91 | — |
| 숨은 문자 처리 | `HIDDEN_CHARACTERS` dict :14-20 | `_INVISIBLE_AND_WS_RE` regex :16-18 | — |
| 비교용 정규화 | — | `strip_for_compare()` :21-23 | — |
| MDX→평문 변환 | — | `normalize_mdx_to_plain()` :26-86 | — |
| 리스트 마커 제거 | — | `strip_list_marker()` :94-96 | — |
| slugify | `slugify()` :44-55 | — | — |

**공백 제거 함수 중복:**

```python
# reverse_sync/text_normalizer.py:21-23
def strip_for_compare(text: str) -> str:
    return _INVISIBLE_AND_WS_RE.sub('', text)

# reverse_sync/sidecar.py:241-243
def _strip_all_ws(text: str) -> str:
    return ''.join(text.split())
```

두 함수 모두 "비교를 위한 공백 제거" 목적이지만 구현이 다릅니다.

**리팩토링 방안:**

1. `text_utils.py`를 공용 텍스트 유틸리티로 확장
2. `text_normalizer.py`의 함수들을 `text_utils.py`로 이관:
   - `collapse_ws()`
   - `normalize_mdx_to_plain()`
   - `strip_for_compare()`
   - `strip_list_marker()`
3. 숨은 문자 처리를 regex 기반(`_INVISIBLE_AND_WS_RE`)으로 통일
4. `sidecar.py`의 `_strip_all_ws()`를 `text_utils.strip_for_compare()`로 대체

**예상 절감:** ~40줄 (text_normalizer.py 삭제 후 text_utils.py 확장)

**실행 결과:** `text_normalizer.py`의 함수들(`strip_for_compare`, `normalize_mdx_to_plain`, `collapse_ws`, `strip_list_marker`, `EMOJI_RE`)을 `text_utils.py`로 이동했습니다. `text_normalizer.py`는 backward-compat re-export 래퍼로 전환했습니다. 5개 파일의 import 경로를 업데이트했습니다.

---

### 2.4 [우선순위 4] 리스트 파싱/렌더링 중복

**중복 파일:**
- `mdx_to_storage/emitter.py:156-223` — `_parse_list_items()`, tree 기반 렌더링
- `reverse_sync/mdx_to_xhtml_inline.py:116-202` — `_parse_list_items()`, 재귀 렌더링

**파싱 로직 비교:**

```python
# mdx_to_storage/emitter.py:156-178
def _parse_list_items(content: str) -> list[_ListNode]:
    for line in content.splitlines():
        expanded = line.expandtabs(4)
        indent = len(expanded) - len(expanded.lstrip(" "))
        depth = max(0, indent // 4)           # indent를 depth로 변환
        ordered_match = _ORDERED_LIST_PATTERN.match(stripped)
        # → _ListNode(ordered, text, depth) 반환

# reverse_sync/mdx_to_xhtml_inline.py:116-158
def _parse_list_items(content: str) -> List[dict]:
    for line in lines:
        indent = len(line) - len(line.lstrip())  # raw indent 사용
        ol_match = re.match(r'^\d+\.\s+(.*)', stripped)
        # → dict(indent, ordered, content) 반환
```

**차이점:**
- emitter.py는 `depth = indent // 4` (레벨 단위), `_ListNode` 클래스 사용
- mdx_to_xhtml_inline.py는 raw indent (공백 수), dict 사용
- 렌더링 방식도 tree 구축 vs 재귀적 구조로 다름

**Regex 패턴 중복:**

```python
# mdx_to_storage/parser.py:9-11
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_ORDERED_PATTERN = re.compile(r"^\d+\.\s+")
_LIST_UNORDERED_PATTERN = re.compile(r"^[-*+]\s+")

# mdx_to_storage/emitter.py:14-16
_ORDERED_LIST_PATTERN = re.compile(r"^\d+\.\s+(.*)$")      # 캡처 그룹 추가
_UNORDERED_LIST_PATTERN = re.compile(r"^[-*+]\s+(.*)$")     # 캡처 그룹 추가
_HEADING_LINE_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")    # _HEADING_PATTERN과 동일
```

**리팩토링 방안:**

1. **공통 regex 패턴 모듈 생성:** `bin/shared/patterns.py`
   ```python
   HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
   LIST_ORDERED_RE = re.compile(r"^(\d+)\.\s+(.*)$")
   LIST_UNORDERED_RE = re.compile(r"^([-*+])\s+(.*)$")
   ```
2. **공통 리스트 파서 생성:** `bin/shared/list_parser.py`
   - 통합 `_parse_list_items()` 함수
   - 공통 `ListItem` 데이터클래스

**예상 절감:** ~50줄

---

### 2.5 [우선순위 5] 사이드카 매핑 생성 중복

**중복 파일:**
- `converter/sidecar_mapping.py` (160줄) — Forward converter가 생성하는 sidecar
- `reverse_sync/sidecar.py` (309줄) — Reverse sync에서 sidecar 로드 및 재생성

**동일 함수명, 다른 구현:**

두 파일 모두 `generate_sidecar_mapping()` 함수를 제공하지만 구현이 다릅니다:

| 속성 | sidecar_mapping.py | sidecar.py |
|------|-------------------|-------------------|
| 매칭 전략 | 순차 1:1 매칭 | 텍스트 기반 lookahead 매칭 |
| 텍스트 비교 | 없음 (순서만 의존) | `collapse_ws` + `_strip_all_ws` |
| Callout 처리 | `_find_callout_range()` | `_count_child_mdx_blocks()` |
| 출력 형식 | 파일 직접 쓰기 (YAML) | YAML 문자열 반환 |
| 매칭 정확도 | 순서 의존 (빠름) | 텍스트 의존 (정확) |

**공통 구조:**
- 두 파일 모두 `record_mapping()` + `parse_mdx_blocks()` 호출
- 두 파일 모두 `NON_CONTENT_TYPES` 필터 적용
- 두 파일 모두 `child_ids` 집합 구성으로 자식 매핑 제외
- 두 파일 모두 `xhtml_xpath`, `xhtml_type`, `mdx_blocks` 구조의 엔트리 생성
- 두 파일 모두 YAML `version: 1` 형식

**`_strip_all_ws()` 중복:**
- `sidecar.py:241-243` — `''.join(text.split())`
- `text_normalizer.py:21-23` (`strip_for_compare`) — `_INVISIBLE_AND_WS_RE.sub('', text)`

**리팩토링 방안:**

1. 매핑 생성의 공통 골격을 추출 (non-content 필터, child_ids 구성, 엔트리 구조)
2. 매칭 전략을 전략 패턴(strategy pattern)으로 분리:
   - `OrderBasedMatcher` (현재 sidecar_mapping.py)
   - `TextBasedMatcher` (현재 sidecar.py)
3. `_strip_all_ws()`를 `text_utils.py`로 이관

**예상 절감:** ~40줄

---

### 2.6 [우선순위 6] 데이터 모델 분산

**분산된 데이터 모델:**

| 모델 | 파일 | 용도 |
|------|------|------|
| `MdxBlock` | `reverse_sync/mdx_block_parser.py:6-12` | MDX 블록 (경량) |
| `Block` | `mdx_to_storage/parser.py:16-25` | MDX 블록 (상세) |
| `BlockMapping` | `reverse_sync/mapping_recorder.py:7-15` | XHTML-MDX 매핑 |
| `SidecarEntry` | `reverse_sync/sidecar.py:11-15` | 사이드카 엔트리 |
| `PageEntry` | `mdx_to_storage/link_resolver.py:18-22` | 페이지 메타데이터 |
| `BlockChange` | `reverse_sync/block_diff.py` | 블록 변경 정보 |
| `_ListNode` | `mdx_to_storage/emitter.py` | 리스트 아이템 |

**리팩토링 방안:**

1. `bin/shared/models.py`에 핵심 데이터 모델 통합:
   - `MdxBlock` + `Block` → 통합 `MdxBlock`
   - `BlockMapping`, `SidecarEntry` 유지 (역할이 다름)
2. 패턴 상수는 `bin/shared/patterns.py`로 통합

---

### 2.7 [우선순위 7] 코드 블록 추출 중복

**중복 파일:**
- `mdx_to_storage/emitter.py:136-144` (`_extract_code_body`)
- `reverse_sync/mdx_to_xhtml_inline.py:264-270` (`_extract_code_language`)

```python
# emitter.py:136-144
def _extract_code_body(block) -> tuple[str, str]:
    lines = block.content.split('\n')
    first = lines[0] if lines else ''
    m = re.match(r'^```(\w*)', first)
    lang = m.group(1) if m else ''
    # ... body 추출

# mdx_to_xhtml_inline.py:264-270
def _extract_code_language(content: str) -> str:
    first_line = content.split('\n')[0]
    m = re.match(r'^```(\w+)', first_line)
    return m.group(1) if m else ''
```

**리팩토링 방안:** 공통 `extract_code_info(content) -> (language, body)` 함수 추출

**예상 절감:** ~10줄

## 3. 리팩토링 로드맵

### Phase 1: 공용 모듈 생성 (기반 작업) — **부분 완료**

`text_utils.py` 확장 완료. `bin/shared/` 디렉토리 생성은 보류 (현재 규모에서는 불필요).

- `emitter.py`의 `_HEADING_LINE_PATTERN`을 `parser.py`의 `HEADING_PATTERN`에서 import하도록 변경 완료.

### Phase 2: MDX 파서 통합 (우선순위 1) — **완료**

1. ~~`mdx_to_storage/parser.py`의 `Block`에 `line_start`, `line_end` 필드 추가~~ ✓
2. ~~`reverse_sync/mdx_block_parser.py`의 호출부를 `mdx_to_storage/parser.py`로 전환~~ ✓
3. ~~`mdx_block_parser.py` 얇은 래퍼로 전환~~ ✓

### Phase 3: 인라인 변환기 통합 (우선순위 2) — **완료**

1. ~~`reverse_sync/mdx_to_xhtml_inline.py`가 `inline.py`의 `convert_inline`을 import하여 사용~~ ✓
2. ~~자체 `_convert_inline()` 삭제~~ ✓

### Phase 4: 텍스트 유틸리티 통합 (우선순위 3) — **완료**

1. ~~`text_normalizer.py`의 모든 함수를 `text_utils.py`로 이관~~ ✓
2. ~~`text_normalizer.py`를 re-export 래퍼로 전환~~ ✓

### Phase 5: 리스트/사이드카/모델 정리 (우선순위 4-7) — 미착수

1. 공통 리스트 파서 모듈 생성
2. 사이드카 매핑의 공통 골격 추출
3. 데이터 모델 통합

## 4. 요약

| 우선순위 | 대상 | 파일 쌍 | 예상 절감 | 상태 |
|---------|------|---------|----------|------|
| 1 | MDX 블록 파서 | `mdx_block_parser.py` ↔ `parser.py` | ~80줄 | **완료** |
| 2 | 인라인 변환기 | `mdx_to_xhtml_inline.py` ↔ `inline.py` | ~50줄 | **완료** |
| 3 | 텍스트 정규화 | `text_normalizer.py` ↔ `text_utils.py` | ~40줄 | **완료** |
| 4 | 리스트 파싱/렌더링 | `emitter.py` ↔ `mdx_to_xhtml_inline.py` | ~50줄 | 미착수 |
| 5 | 사이드카 매핑 | `sidecar_mapping.py` ↔ `sidecar.py` | ~40줄 | 미착수 |
| 6 | 데이터 모델 | 5개 파일에 분산 | ~20줄 | 미착수 |
| 7 | 코드 블록 추출 | `emitter.py` ↔ `mdx_to_xhtml_inline.py` | ~10줄 | 미착수 |
| | **합계** | | **~290줄** (완료 ~170줄) | |

### 리팩토링 시 주의사항

1. **테스트 커버리지:** 310+ 유닛 테스트, 19 E2E 시나리오가 존재합니다. 리팩토링 후 전체 테스트 통과를 반드시 확인해야 합니다.
2. **import 경로 변경:** 모듈 통합 시 `reverse_sync_cli.py`, `converter/cli.py` 등 진입점의 import 경로 업데이트가 필요합니다.
3. **점진적 진행:** Phase 별로 나누어 진행하고, 각 Phase 완료 후 전체 테스트를 실행하는 것을 권장합니다.
4. **sidecar_mapping vs sidecar_lookup:** 매칭 전략이 다르므로(순서 vs 텍스트) 통합 시 두 전략을 모두 보존해야 합니다.
