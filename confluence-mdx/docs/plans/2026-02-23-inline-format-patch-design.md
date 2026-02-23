# Reverse-Sync Inline Format Patch 설계

## 날짜

2026-02-23

## 문제

Reverse-sync에서 MDX 교정 시 inline code(backtick) 표기가 새로 추가되거나 제거될 때,
XHTML에 `<code>` 태그가 반영되지 않습니다.

### 재현 사례

```
# 원본 MDX (backtick 없음)
QueryPie는 https://querypie-poc.customer.com/과 같은 TLS 인증서가 적용된...

# 교정된 MDX (backtick 추가)
QueryPie는 `https://querypie-poc.customer.com/`과 같은 TLS 인증서가 적용된...

# 패치된 XHTML (문제: <code> 태그 미생성)
QueryPie는 https://querypie-poc.customer.com/과 같은...
# ↑ plain text만 변경되고, <code> 태그가 생성되지 않음
```

### 근본 원인

`patch_builder.py`의 `build_patches()`에서 `normalize_mdx_to_plain()`이 backtick을 제거하므로
(`text_utils.py:142`의 `` re.sub(r'`([^`]+)`', r'\1', s) ``),
inline code 추가/제거 정보가 소실됩니다.
결과적으로 `xhtml_patcher.py`의 `_apply_text_changes()`는 기존 HTML 태그 구조를 보존하면서
텍스트만 바꾸기 때문에 새 `<code>` 태그를 생성할 수 없습니다.

## 해결 방안

### 접근 방식: Inline 변경 감지 + `new_inner_xhtml` 패치 전환

old/new MDX 콘텐츠의 inline 포맷 마커(backtick, bold, italic, link)를 비교하여
변경이 감지되면 text patch 대신 `new_inner_xhtml` 패치를 생성합니다.

`new_inner_xhtml` 패치는 이미 `xhtml_patcher.py`의 `_replace_inner_html()`에서 지원되므로,
변경은 `patch_builder.py`에 집중됩니다.

### 1. Inline 변경 감지 함수

`patch_builder.py`에 4개의 regex 패턴과 3개의 함수를 추가합니다:

- `_extract_inline_markers(content)` — MDX content에서 code/bold/italic/link 마커를 위치순으로 추출
- `_strip_positions(markers)` — 비교 시 위치 정보를 제거하여 false positive 방지
- `has_inline_format_change(old, new)` — 마커를 추출·비교하여 inline 포맷 변경 여부를 판정

> **구현:** [`bin/reverse_sync/patch_builder.py:20-51`](../bin/reverse_sync/patch_builder.py#L20-L51)
> **테스트:** [`tests/test_reverse_sync_patch_builder.py:932-1023`](../tests/test_reverse_sync_patch_builder.py#L932-L1023)

**설계 노트:** 원래 계획에서는 `has_inline_format_change()`가 마커를 직접 비교했으나,
주변 텍스트 변경 시 마커 위치가 이동하여 false positive가 발생하는 문제가 있었습니다.
이를 해결하기 위해 `_strip_positions()` 헬퍼를 추가하여 type+content만 비교하도록 개선했습니다.

### 2. Patch 생성 분기

`build_patches()`의 direct 전략에서, `has_inline_format_change()`가 True를 반환하면
`mdx_block_to_inner_xhtml()`로 XHTML inner HTML을 생성하여 `new_inner_xhtml` 패치를 발행합니다.
False인 경우 기존 `new_plain_text` text patch 로직을 유지합니다.

> **구현:** [`bin/reverse_sync/patch_builder.py:266-288`](../bin/reverse_sync/patch_builder.py#L266-L288) (direct 전략)
> **구현:** [`bin/reverse_sync/patch_builder.py:491-524`](../bin/reverse_sync/patch_builder.py#L491-L524) (list item 전략)
> **테스트:** [`tests/test_reverse_sync_patch_builder.py:287`](../tests/test_reverse_sync_patch_builder.py#L287) (`TestBuildPatches` 클래스)
> **테스트:** [`tests/test_reverse_sync_patch_builder.py:607`](../tests/test_reverse_sync_patch_builder.py#L607) (`TestBuildListItemPatches` 클래스)

### 3. 블록 유형별 지원

| 블록 유형 | 전략 | 처리 방식 |
|-----------|------|-----------|
| paragraph | direct | `mdx_block_to_inner_xhtml(content, 'paragraph')` |
| heading | direct | `mdx_block_to_inner_xhtml(content, 'heading')` |
| list | list (`build_list_item_patches`) | 항목별 inline 변경 감지, `convert_inline(item)` |
| callout/table 내 | containing | text patch 유지 (향후 필요 시 별도 처리) |

### 4. 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| [`bin/reverse_sync/patch_builder.py`](../bin/reverse_sync/patch_builder.py) | `has_inline_format_change()`, `_extract_inline_markers()`, `_strip_positions()` 추가; direct/list 전략에 분기 추가 |
| `bin/reverse_sync/mdx_to_xhtml_inline.py` | 변경 없음 (이미 `mdx_block_to_inner_xhtml` 지원) |
| `bin/reverse_sync/xhtml_patcher.py` | 변경 없음 (이미 `new_inner_xhtml` 패치 지원) |
| [`tests/test_reverse_sync_patch_builder.py`](../tests/test_reverse_sync_patch_builder.py) | 21개 테스트 추가 (inline marker 추출/감지 15개 + 패치 생성 6개) |

## 검증 결과

- `bin/reverse_sync_cli.py verify --branch=split/ko-proofread-20260221-overview` 실행 시
  `system-architecture-overview.mdx`의 backtick verify diff가 해결되었습니다.
- 152개 관련 테스트 전부 통과합니다 (patch_builder 91 + mdx_to_xhtml_inline 47 + xhtml_patcher 14).
