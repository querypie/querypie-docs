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

`patch_builder.py`의 `build_patches()`에서 `normalize_mdx_to_plain()`이 backtick을 제거하므로,
inline code 추가/제거 정보가 소실됩니다. 결과적으로 `_apply_text_changes()`는 기존 HTML 태그 구조를
보존하면서 텍스트만 바꾸기 때문에 새 `<code>` 태그를 생성할 수 없습니다.

## 해결 방안

### 접근 방식: Inline 변경 감지 + `new_inner_xhtml` 패치 전환

old/new MDX 콘텐츠의 inline 포맷 마커(backtick, bold, italic, link)를 비교하여
변경이 감지되면 text patch 대신 `new_inner_xhtml` 패치를 생성합니다.

`new_inner_xhtml` 패치는 이미 `xhtml_patcher.py`의 `_replace_inner_html()`에서 지원되므로,
변경은 `patch_builder.py`에 집중됩니다.

### 1. Inline 변경 감지 함수

`patch_builder.py`에 추가:

```python
_CODE_SPAN_RE = re.compile(r'`([^`]+)`')
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_ITALIC_RE = re.compile(r'(?<!\*)\*([^*]+)\*(?!\*)')
_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

def has_inline_format_change(old_content: str, new_content: str) -> bool:
    """old/new MDX 콘텐츠의 inline 포맷 마커가 다른지 감지한다."""
    return _extract_inline_markers(old_content) != _extract_inline_markers(new_content)

def _extract_inline_markers(content: str) -> list:
    """MDX content에서 inline 포맷 마커를 순서대로 추출한다."""
    markers = []
    for m in _CODE_SPAN_RE.finditer(content):
        markers.append(('code', m.start(), m.group(1)))
    for m in _BOLD_RE.finditer(content):
        markers.append(('bold', m.start(), m.group(1)))
    for m in _ITALIC_RE.finditer(content):
        markers.append(('italic', m.start(), m.group(1)))
    for m in _LINK_RE.finditer(content):
        markers.append(('link', m.start(), m.group(1), m.group(2)))
    return sorted(markers, key=lambda x: x[1])
```

### 2. Patch 생성 분기

`build_patches()`의 direct 전략에서:

```python
# strategy == 'direct'
if has_inline_format_change(change.old_block.content, change.new_block.content):
    new_inner = mdx_block_to_inner_xhtml(change.new_block.content, change.new_block.type)
    patches.append({
        'xhtml_xpath': mapping.xhtml_xpath,
        'old_plain_text': mapping.xhtml_plain_text,
        'new_inner_xhtml': new_inner,
    })
else:
    # 기존 text patch 로직 유지
    ...
```

### 3. 블록 유형별 지원

| 블록 유형 | 전략 | 처리 방식 |
|-----------|------|-----------|
| paragraph | direct | `mdx_block_to_inner_xhtml(content, 'paragraph')` |
| heading | direct | `mdx_block_to_inner_xhtml(content, 'heading')` |
| list | list (`build_list_item_patches`) | 항목별 inline 변경 감지, `convert_inline(item)` |
| callout/table 내 | containing | containing block 전체에 대해 `new_inner_xhtml` 생성 |

### 4. 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `patch_builder.py` | `has_inline_format_change()`, `_extract_inline_markers()` 추가; direct/containing/list 전략에 분기 추가 |
| `mdx_to_xhtml_inline.py` | 변경 없음 (이미 `mdx_block_to_inner_xhtml` 지원) |
| `xhtml_patcher.py` | 변경 없음 (이미 `new_inner_xhtml` 패치 지원) |
| 테스트 | inline code 추가/제거 케이스 테스트 추가 |

## 검증 기준

- `bin/reverse_sync_cli.py verify --branch=split/ko-proofread-20260221-overview` 실행 시
  `system-architecture-overview.mdx`의 backtick verify diff가 사라져야 합니다.
- 기존 21개 regression 테스트 케이스 전부 통과해야 합니다.
