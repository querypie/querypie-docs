# Reverse Sync 전면 재구성 설계

> 작성일: 2026-03-13
> 연관 분석: `analysis-reverse-sync-refactoring.md`

> **설계 범위 원칙**
> 이 문서의 모든 설계와 구현은 `tests/testcases/`에 실제로 존재하는 XHTML/MDX 사례에 기반한다.
> 실제 사례로 확인되지 않은 가설적 케이스에 대한 예외 처리는 이 설계의 커버 범위 밖이다.
> 새로운 케이스가 발견되면 testcase를 먼저 추가하고, 그 이후 설계·구현을 보완하는 사이클로 진행한다.

---

## 1. 배경 및 동기

### 1.1 현재 아키텍처의 문제

Reverse Sync의 현재 접근 방식은 **"XHTML을 최대한 건드리지 않고 텍스트 차이만 이식"** 하는 전략이다. 이 전략은 Confluence 전용 요소(`<ac:image>`, `<ac:link>` 등)를 보호하기 위해 선택되었지만, 구현이 진행될수록 다음과 같은 기술부채가 쌓이고 있다.

- `patch_builder.py`의 전략 분기가 5가지(direct / containing / list / table / skip)로 늘어났고, 각 분기마다 예외 케이스가 추가되고 있다.
- `_resolve_child_mapping()`이 4단계, `_resolve_mapping_for_change()`가 6단계 폴백 체인을 갖는다.
- 버그를 수정할수록 새로운 edge case가 발견되는 패턴이 반복된다 (PR #852, #853, #866, #888, #903).
- `text_transfer.py`의 문자 단위 위치 정렬은 두 좌표계(MDX ↔ XHTML) 사이의 매핑으로, 본질적으로 불안정하다.

### 1.2 대안적 접근: MDX → XHTML 전체 재구성

변경된 MDX 블록을 **XHTML로 직접 재구성**하고, 소실된 Confluence 요소만 원본에서 선택적으로 복원하면 위의 복잡도를 근본적으로 제거할 수 있다.

```
[현재] MDX diff → 텍스트 변경 추출 → XHTML 내 텍스트 위치 매핑 → 문자 단위 치환
[제안] MDX diff → 변경 블록 재구성 → lossy 요소 재주입 → XHTML 교체
```

`mdx_block_to_xhtml_element()`는 이미 `_build_insert_patch()`에서 사용되고 있다. 이를 **수정(modified) 블록에도 적용**하는 것이 이 설계의 핵심이다.

---

## 2. 재구성이 막히는 두 가지 근본 문제

### 문제 A: 리스트 항목 내 lossy 요소의 위치를 모름

리스트 항목 안에 `<ac:image>`, `<ac:link>`, `<span style=...>` 같은 요소가 있어도 MDX에는 표현되지 않는다. 재구성 시 이 요소들을 어느 `<li>`의 어느 위치에 넣어야 할지 알 수 없다.

```xml
<!-- 원본 XHTML -->
<ul>
  <li><p>item 1</p><ac:image><ri:attachment ri:filename="img.png"/></ac:image></li>
  <li><p>item 2</p></li>
</ul>

<!-- MDX — ac:image 없음 -->
* item 1
* item 2
```

재구성 후 `<ac:image>`를 어디에 넣어야 할지 알려주는 정보가 현재 sidecar에 없다.

### 문제 B: Callout 내부 복합 구조를 재구성하지 못함

MDX에서 callout 내부는 단순한 텍스트 블록이지만, XHTML에서는 `<p>`, `<ul>`, `<ac:structured-macro ac:name="code">` 등이 중첩된 구조다. 현재 `_convert_callout_inner()`는 내부를 단일 paragraph로만 변환하므로, 내부에 리스트나 코드 블록이 있으면 구조가 무너진다.

```mdx
<Callout type="info">
  단락 텍스트

  * 리스트 항목 1
  * 리스트 항목 2
</Callout>
```

→ 현재: `<p>단락 텍스트 * 리스트 항목 1 * 리스트 항목 2</p>` (틀림)
→ 목표: `<p>단락 텍스트</p><ul><li><p>리스트 항목 1</p></li>...` (맞음)

---

## 3. 해결 방안

### 3.1 문제 A 해결: Sidecar 플랫 매핑 + ref 참조 구조

#### 핵심 원칙

`<ul>`/`<ol>`과 `<li>` 모두 **최상위 sidecar entry**로 나열하고, 부모-자식 관계는 `children` ref 목록으로 표현한다.

- `ul`/`ol` entry → `children: [li xhtml_xpath 목록]`
- `li` entry → `plain_text`, `inline_trailing_html`, `children: [block child xhtml_xpath 목록]`
- `<li>` 내부의 block 요소 (`<ul>`, `<ol>`, `<ac:structured-macro>` 등)도 독립 entry — `li` entry의 `children`에서 참조

이 구조는 `ul`-`li` 관계와 `li`-block child 관계를 동일한 패턴으로 처리하므로, 어떤 깊이의 nesting도 추가 설계 없이 커버된다. nested list의 이중 삽입 문제가 구조적으로 제거된다.

#### Sidecar 스키마 변경

```yaml
# 기존
mappings:
  - xhtml_xpath: ul[1]
    xhtml_type: list
    mdx_blocks: [5]

# 변경 후 — ul, li 모두 최상위 entry, 관계는 children ref 로 표현
# xhtml_type 은 XHTML 태그명 그대로 사용 (ul, ol, li, p, ac:image 등)
mappings:
  - xhtml_xpath: ul[1]
    xhtml_type: ul
    mdx_blocks: [5]
    children:
      - ref: "ul[1]/li[1]"
      - ref: "ul[1]/li[2]"

  - xhtml_xpath: ul[1]/li[1]
    xhtml_type: li
    plain_text: "item 1 설명 텍스트"           # inline 매칭 키
    inline_trailing_html: >-
      <ac:image><ri:attachment
      ri:filename="img.png"/></ac:image>        # <p> 직후 non-block lossy 요소만
    children:
      - ref: "ul[1]/li[1]/ul[1]"               # block child 참조

  - xhtml_xpath: ul[1]/li[1]/ul[1]
    xhtml_type: ul
    children:
      - ref: "ul[1]/li[1]/ul[1]/li[1]"

  - xhtml_xpath: ul[1]/li[1]/ul[1]/li[1]
    xhtml_type: li
    plain_text: "sub-item A"
    inline_trailing_html: ""
    children: []

  - xhtml_xpath: ul[1]/li[2]
    xhtml_type: li
    plain_text: "item 2 텍스트"
    inline_trailing_html: ""
    children: []
```

`inline_trailing_html`은 `<p>` 직후의 **non-block** 요소만 저장한다. `<ul>`, `<ol>`, `<ac:structured-macro>` 등 block 요소는 `children` ref로 분리하므로 저장 대상이 아니다.

#### 생성: `_process_element()` 재귀 처리

```python
def _process_element(elem, xpath: str) -> list[SidecarEntry]:
    """ul/ol/li 요소를 재귀 처리하여 독립 SidecarEntry 목록을 반환한다.

    모든 요소는 최상위 entry 로 생성되고, 부모-자식 관계는 children ref 로 표현된다.
    """
    entries = []

    if elem.name in ('ul', 'ol'):
        children_refs = []
        for li_idx, li in enumerate(elem.find_all('li', recursive=False), start=1):
            li_xpath = f"{xpath}/li[{li_idx}]"
            children_refs.append({'ref': li_xpath})
            entries.extend(_process_element(li, li_xpath))

        entries.insert(0, SidecarEntry(
            xhtml_xpath=xpath,
            xhtml_type=elem.name,   # 'ul' 또는 'ol' — XHTML 태그명 그대로
            children=children_refs,
        ))

    elif elem.name == 'li':
        # Confluence storage format에서 <li> 내부는 항상 <p>로 래핑됨.
        # <p> 없는 <li>는 실제로 존재하지 않는 케이스이므로 별도 처리 불필요.
        p_elem = elem.find('p')
        plain_text = p_elem.get_text(separator=' ', strip=True) if p_elem else ''

        # inline trailing: <p> 직후 non-block 형제 요소
        inline_trailing = []
        block_children_refs = []
        block_counters = {}

        if p_elem:
            for sib in p_elem.next_siblings:
                if not hasattr(sib, 'name'):
                    continue
                if sib.name in ('ul', 'ol') or _is_block_macro(sib):
                    tag = sib.name
                    block_counters[tag] = block_counters.get(tag, 0) + 1
                    child_xpath = f"{xpath}/{tag}[{block_counters[tag]}]"
                    block_children_refs.append({'ref': child_xpath})
                    entries.extend(_process_element(sib, child_xpath))
                else:
                    inline_trailing.append(str(sib))

        entries.insert(0, SidecarEntry(
            xhtml_xpath=xpath,
            xhtml_type='li',        # XHTML 태그명 그대로
            plain_text=plain_text,
            inline_trailing_html=''.join(inline_trailing),
            children=block_children_refs,
        ))

    return entries
```

#### 소비: `reconstruct_ul_entry()` / `reconstruct_li_entry()` — `_ListNode` tree 위치 기반 매칭

MDX 파서(`parse_mdx_blocks()`)는 nested list 전체를 하나의 `list` 블록으로 반환하고, 구조화는 하지 않는다. `emitter.py`에 이미 존재하는 `_parse_list_items()` + `_build_list_tree()`를 재사용하여 `_ListNode` tree를 생성하고, sidecar `children` refs와 **위치 기반(zip)** 으로 매칭한다.

텍스트 기반 큐(`pop_inline_item()`) 없이 위치 기반으로만 동작하므로, 동일 텍스트 항목이 여럿 있어도 충돌이 없다.

```python
def reconstruct_ul_entry(
    entry: SidecarEntry,
    sidecar_index: dict,
    mdx_nodes: list[_ListNode],    # 이 ul/ol 레벨의 MDX 항목들 (_ListNode)
) -> str:
    """ul/ol entry를 재구성한다.

    sidecar children refs와 mdx_nodes를 위치(zip)로 매칭한다.
    emitter._parse_list_items() + _build_list_tree()로 생성한 _ListNode tree를 인자로 받는다.

    항목 수 불일치 처리:
      - MDX 항목이 더 많음(추가): zip 이후 남은 mdx_nodes를 sidecar 없이 재구성
      - MDX 항목이 더 적음(삭제): zip이 짧은 쪽에서 멈추므로 삭제 항목은 자동 생략
    """
    tag = entry.xhtml_type  # 'ul' or 'ol' — XHTML 태그명 그대로
    sidecar_refs = entry.children or []
    parts = []

    # sidecar가 있는 항목: ref + node 위치 매칭
    for ref_dict, node in zip(sidecar_refs, mdx_nodes):
        li_entry = sidecar_index.get(ref_dict['ref'])
        if li_entry:
            parts.append(reconstruct_li_entry(li_entry, sidecar_index, node))

    # sidecar보다 MDX 항목이 많으면 — 새로 추가된 항목, sidecar 없이 재구성
    for node in mdx_nodes[len(sidecar_refs):]:
        parts.append(f'<li><p>{convert_inline(node.text)}</p></li>')

    return f'<{tag}>{"".join(parts)}</{tag}>'


def reconstruct_li_entry(
    entry: SidecarEntry,
    sidecar_index: dict,
    node: _ListNode,               # 이 li에 대응하는 MDX _ListNode
) -> str:
    """li entry를 재구성한다.

    node.text — li 본문 MDX 텍스트
    node.children — 이 li의 nested list 항목들 (nested ul/ol 재구성에 전달)
    """
    li_inner = f'<p>{convert_inline(node.text)}</p>'
    li_inner += entry.inline_trailing_html or ''

    for ref_dict in (entry.children or []):
        child = sidecar_index.get(ref_dict['ref'])
        if child is None:
            continue
        if child.xhtml_type in ('ul', 'ol'):
            # node.children = 이 li의 nested list 항목들
            li_inner += reconstruct_ul_entry(child, sidecar_index, node.children)
        else:
            # block macro 등 기타 block children — 원본 xhtml_fragment 그대로
            li_inner += child.xhtml_fragment or ''
    return f'<li>{li_inner}</li>'


# 진입점 (patch_builder.py에서 list 블록 처리 시)
# emitter.py의 기존 함수 재사용
items = _parse_list_items(new_block.content)   # bin/mdx_to_storage/emitter.py
roots = _build_list_tree(items)                # bin/mdx_to_storage/emitter.py
xhtml = reconstruct_ul_entry(sidecar_entry, sidecar_index, roots)
```
```

#### 처리 가능한 케이스 분류

| 케이스 | 처리 방법 |
|--------|-----------|
| 항목 내용 변경 + lossy 없음 | `li` entry 재구성 (clean) |
| 항목 내용 변경 + inline lossy 있음 | 재구성 + `inline_trailing_html` 재주입 |
| 항목 내 nested list 있음 | `li` entry의 `children` → `ul`/`ol` entry 재구성 (이중 삽입 구조적 불가) |
| 항목 추가 (MDX > sidecar) | `zip()` 이후 남은 `mdx_nodes`를 sidecar 없이 재구성 — `inline_trailing_html` 없음 |
| 항목 삭제 (MDX < sidecar) | `zip()`이 짧은 쪽에서 멈추므로 삭제 항목 자동 생략 |
| 깊이 무관한 nesting | `reconstruct_entry()` 재귀로 동일하게 처리 |

---

> **TODO — 구현 전 조사 필요**
>
> 1. **[Phase 1 선결] 현재 `generate_sidecar_mapping()`의 `li` 처리 여부**: `<li>`에 대해 독립 entry를 이미 생성하는지, 아니면 `<ul>`/`<ol>` entry 안에 포함하는지 확인. `_process_element()` 도입 시 기존 entry 생성 로직과의 충돌 범위 파악 필요.
>
> 2. **[Phase 1 선결] `xhtml_type` 태그명 일치 확인**: `xhtml_type`은 XHTML 태그명 그대로 사용한다 (`ul`, `ol`, `li`, `p`, `ac:image` 등). 기존 sidecar에 추상 타입(`list`, `list_item`)이 저장된 경우 마이그레이션 또는 역직렬화 시 변환 필요 여부 확인.
>
> 3. **[Phase 1 선결] `xhtml_xpath` 포맷**: nested element의 xpath `ul[1]/li[1]/ul[1]` 형식이 현재 `mapping_recorder.py`의 xpath 생성 방식과 일치하는지 확인 필요.
>
> 4. **[Phase 1 선결] `_parse_list_items()` / `_build_list_tree()` 접근성 확인**: `emitter.py`의 두 함수가 모듈 외부에서 import 가능한지 확인. private 함수(`_`prefix)이므로 `reverse_sync` 패키지에서 호출 가능한 형태로 노출 필요 여부 검토.
>
> 5. **[Phase 1 선결] `_is_block_macro()` 판별 기준**: `<ac:structured-macro>`가 block child로 분류되어야 할 케이스와 inline trailing으로 남아야 할 케이스 구분 기준 확인 필요.
>
> 6. **[조사] 다단락 `<li>` 존재 여부**: `<li><p>para1</p><p>para2</p></li>` 형태가 실제 Confluence XHTML에 존재하는지 testcase 전수 조사. 추측으로는 존재하지 않으며, 단일 `<p>` 내에서 `<br/>` 줄바꿈만 사용하는 것으로 보임. 존재하지 않음이 확인되면 단순 케이스로 간주하고 별도 처리 불필요. 존재하면 두 번째 `<p>`를 `inline_trailing_html`에 보존하는 방향 검토.

---

### 3.1.1 Paragraph 내 inline-block 요소 처리 — ParagraphEditSequence 기반

`<p>` 내부에 텍스트와 lossy inline-block 요소(`<ac:image>` 등)가 혼재하는 경우, list-item과 동일한 원칙을 적용한다: lossy 요소는 **독립 sidecar entry**로 분리하고, `paragraph` entry의 `children`에서 ref로 참조한다.

텍스트 편집이 발생한 경우, old MDX → new MDX의 **ParagraphEditSequence**(Myers diff 기반)를 구하여 각 `AnchorSegment`의 삽입 위치를 old 좌표에서 new 좌표로 정확히 매핑한다. fuzzy 매칭은 사용하지 않는다. 설계가 커버하지 못하는 케이스는 명시적으로 실패시키고, 테스트케이스를 보강하는 사이클로 해결한다.

#### 용어 정의

```
ParagraphEditSequence = list[InlineSegment]

InlineSegment
├── TextSegment(text: str)      # diff 대상 텍스트 조각
└── AnchorSegment(ref: str)     # ac:image 등 lossy inline-block — 위치 고정 앵커
```

`<p>` 하나는 하나의 `ParagraphEditSequence`로 표현된다. `TextSegment`와 `AnchorSegment`가 교차하는 시퀀스이며, edit(Myers diff)는 `TextSegment`에만 적용된다. `AnchorSegment`는 인접 `TextSegment`의 위치 변화를 따라 new 좌표로 매핑된다.

#### Sidecar 스키마

`<p>` 내부를 `TextSegment`(`kind: text`)와 `AnchorSegment`(`kind: ref`) 교차 시퀀스로 표현한다. `TextSegment.text`는 MDX 텍스트 조각(`convert_inline()` 출력)이며, `AnchorSegment`의 위치를 정의하는 좌표 기준이 된다. TextSegments를 이어 붙이면 해당 단락의 MDX 텍스트(`old_mdx_text`)와 정확히 일치한다.

```yaml
- xhtml_xpath: p[1]
  xhtml_type: p
  children:
    - kind: text
      text: "텍스트A "            # TextSegment — MDX 텍스트 조각 (convert_inline 출력)
    - kind: ref
      ref: "p[1]/ac:image[1]"    # AnchorSegment — 이 TextSegment 직후 위치
    - kind: text
      text: " 텍스트B"            # TextSegment — MDX 텍스트 조각
    - kind: ref
      ref: "p[1]/ac:image[2]"    # AnchorSegment

- xhtml_xpath: p[1]/ac:image[1]
  xhtml_type: ac:image
  html: "<ac:image><ri:attachment ri:filename='img1.png'/></ac:image>"

- xhtml_xpath: p[1]/ac:image[2]
  xhtml_type: ac:image
  html: "<ac:image><ri:attachment ri:filename='img2.png'/></ac:image>"
```

신규 sidecar는 `ac:image` 존재 여부와 무관하게 **항상** `children`을 구성한다. `ac:image`가 없는 경우 `children = [{'kind': 'text', 'text': '전체텍스트'}]` 형태가 된다. `children`이 없는 entry는 구 sidecar에 대한 backward compat 폴백으로만 사용된다.

#### 생성: `_process_paragraph()` — 항상 교차 시퀀스로 구성

`TextSegment.text`는 XHTML plain text가 아닌 **MDX 텍스트 조각**을 저장한다. XHTML 조각을 누적한 뒤 `convert_inline()`을 적용하면, TextSegments를 이어 붙인 결과가 해당 단락의 MDX 텍스트와 정확히 일치한다. 이로써 `reconstruct_paragraph()`에서 별도 normalization 없이 `old_text == old_mdx_text`가 항상 성립한다.

```python
def _process_paragraph(elem, xpath: str) -> list[SidecarEntry]:
    """<p> 요소를 처리하여 ParagraphEditSequence 구조의 sidecar entry를 생성한다.

    ac:image 존재 여부와 무관하게 항상 TextSegment/AnchorSegment 교차 시퀀스로 children을 구성한다.
      - ac:image 없음: children = [{'kind': 'text', 'text': '전체MDX텍스트'}]
      - ac:image 있음: [text, ref, text, ref, ..., text] 교차 시퀀스

    TextSegment.text는 MDX 텍스트 조각이다 — XHTML 조각(strong, em, code 등)을
    convert_inline()으로 변환한 결과. TextSegments 연결 = 해당 단락의 MDX 텍스트.
    """
    entries = []
    children = []
    image_counters = {}
    cursor_xhtml = ''  # <p> 내 텍스트/인라인 요소의 XHTML 조각 누적

    for child in elem.children:
        if hasattr(child, 'name') and child.name == 'ac:image':
            # 직전 TextSegment flush — 누적 XHTML을 MDX 텍스트로 변환 (빈 문자열도 포함)
            children.append({'kind': 'text', 'text': convert_inline(cursor_xhtml)})
            cursor_xhtml = ''
            # AnchorSegment
            image_counters['ac:image'] = image_counters.get('ac:image', 0) + 1
            img_xpath = f"{xpath}/ac:image[{image_counters['ac:image']}]"
            children.append({'kind': 'ref', 'ref': img_xpath})
            # ac:image 독립 entry
            entries.append(SidecarEntry(
                xhtml_xpath=img_xpath,
                xhtml_type='ac:image',
                html=str(child),
            ))
        else:
            # 텍스트 노드(NavigableString) 또는 인라인 요소(strong, em, code 등) — XHTML 조각 누적
            cursor_xhtml += str(child)

    # 마지막 TextSegment flush (항상 추가 — ac:image 없어도 전체 텍스트가 여기에 들어감)
    children.append({'kind': 'text', 'text': convert_inline(cursor_xhtml)})

    entries.insert(0, SidecarEntry(
        xhtml_xpath=xpath,
        xhtml_type='p',
        children=children,
    ))
    return entries
```

#### ParagraphEditSequence를 이용한 AnchorSegment 위치 매핑

```
old_seq = ParagraphEditSequence from sidecar:
  [TextSegment("텍스트A "), AnchorSegment(ref[1]), TextSegment(" 텍스트B"), AnchorSegment(ref[2])]

old_text = TextSegment 연결: "텍스트A  텍스트B"
new_text = 새 MDX: "수정된텍스트A 수정된텍스트B"

AnchorSegment 위치 (old 좌표):
  ref[1]: old_pos = len("텍스트A ")  = 5   (TextSegment[0] 끝)
  ref[2]: old_pos = len("텍스트A  텍스트B") = 11  (TextSegment[1] 끝)

Myers diff edit ops (TextSegment 연결 텍스트 기준):
  DELETE  "텍스트A"   (old 0..4)
  INSERT  "수정된텍스트A"
  RETAIN  " "         (old 5)    ← ref[1] old_pos=5 → new_pos 여기서 결정
  DELETE  " 텍스트B"  (old 6..11)
  INSERT  " 수정된텍스트B"
                                 ← ref[2] old_pos=11 → new_pos 여기서 결정

매핑 결과:
  ref[1]: new_pos = 8   ("수정된텍스트A " 이후)
  ref[2]: new_pos = 18  (" 수정된텍스트B" 이후)

재구성:
  new_text[:8] + image[1].html + new_text[8:18] + image[2].html + new_text[18:]
  = "수정된텍스트A " + <ac:image[1]> + " 수정된텍스트B" + <ac:image[2]>
```

#### 구현

```python
def map_anchor_positions(
    old_text: str,
    new_text: str,
    old_positions: list[int],   # unit: Python str index (Unicode code point)
) -> list[int]:                 # unit: Python str index (Unicode code point)
    """Myers diff edit sequence로 AnchorSegment의 old 좌표를 new 좌표로 매핑한다.

    좌표 단위: Python str index (Unicode code point).
    한국어/영어 텍스트에서 code point = grapheme cluster이므로 실용상 문제 없음.
    이모지 결합 문자(ZWJ sequence) 등 edge case가 발생하면 그때 testcase 추가 후 대응한다.

    edit op:
      ('retain', n) — old n code points 유지 → old_ptr += n, new_ptr += n
      ('delete', n) — old n code points 삭제 → old_ptr += n
      ('insert', s) — new s 삽입 → new_ptr += len(s)  (len = code point 수)

    AnchorSegment position은 TextSegment 끝(직후)에 위치하므로:
      old_ptr 이 old_pos 에 도달하는 시점의 new_ptr 를 기록한다.
    """
    ops = myers_diff(old_text, new_text)  # → list of (op, value)
    old_ptr = 0
    new_ptr = 0
    pos_iter = iter(sorted(old_positions))
    next_pos = next(pos_iter, None)
    new_positions = []

    for op, value in ops:
        if next_pos is None:
            break
        if op == 'retain':
            n = value
            while next_pos is not None and old_ptr + n >= next_pos:
                offset = next_pos - old_ptr
                new_positions.append(new_ptr + offset)
                next_pos = next(pos_iter, None)
            old_ptr += n
            new_ptr += n
        elif op == 'delete':
            n = value
            while next_pos is not None and old_ptr + n >= next_pos:
                # 삭제 구간 안에 AnchorSegment → delete 직후 new_ptr 로 매핑
                new_positions.append(new_ptr)
                next_pos = next(pos_iter, None)
            old_ptr += n
        elif op == 'insert':
            new_ptr += len(value)

    # 남은 position은 old_text 끝 이후 → new_text 끝으로 매핑
    while next_pos is not None:
        new_positions.append(len(new_text))
        next_pos = next(pos_iter, None)

    return new_positions


def reconstruct_paragraph(
    old_mdx_text: str,
    new_mdx_text: str,
    entry: SidecarEntry,
    sidecar_index: dict,
) -> str:
    """paragraph를 ParagraphEditSequence 기반으로 재구성한다.

    children이 없으면 새 MDX 텍스트를 그대로 변환한다 (구 sidecar backward compat 폴백).
    children이 있으면:
      - TextSegment 연결 = 해당 단락의 MDX 텍스트 → old_mdx_text와 직접 비교 (normalization 불필요)
      - AnchorSegment가 없는 경우(ac:image 없음): convert_inline 적용
      - AnchorSegment가 있는 경우: map_anchor_positions()로 위치 매핑 후 new_text에 삽입
    old_mdx_text가 TextSegment 연결과 일치하지 않으면 SidecarMismatchError를 발생시킨다.
    """
    if not entry.children:
        return f'<p>{convert_inline(new_mdx_text)}</p>'

    # ParagraphEditSequence 복원
    text_segments = [c['text'] for c in entry.children if c['kind'] == 'text']  # TextSegment
    anchor_refs = [c['ref'] for c in entry.children if c['kind'] == 'ref']      # AnchorSegment
    old_text = ''.join(text_segments)

    if old_text != old_mdx_text:
        raise SidecarMismatchError(
            f"paragraph TextSegment mismatch:\n"
            f"  sidecar: {old_text!r}\n"
            f"  actual:  {old_mdx_text!r}\n"
            f"  → sidecar 재생성 필요 (testcase fixture 업데이트)"
        )

    # AnchorSegment old 좌표 계산 (TextSegment 누적 길이)
    old_positions = []
    cursor = 0
    seg_iter = iter(text_segments)
    for child in entry.children:
        if child['kind'] == 'text':
            cursor += len(next(seg_iter))
        elif child['kind'] == 'ref':
            old_positions.append(cursor)

    # Myers diff로 AnchorSegment new 좌표 매핑
    new_positions = map_anchor_positions(old_text, new_mdx_text, old_positions)

    # new_mdx_text를 MDX 좌표로 먼저 분할한 뒤, 각 조각에 convert_inline() 적용
    result = ''
    prev = 0
    for ref, new_pos in zip(anchor_refs, new_positions):
        mdx_piece = new_mdx_text[prev:new_pos]          # MDX 좌표로 MDX 텍스트 분할
        result += convert_inline(mdx_piece)              # 분할 후 XHTML 변환
        ref_entry = sidecar_index.get(ref)
        if ref_entry is None:
            raise SidecarMismatchError(f"AnchorSegment ref not found in sidecar_index: {ref!r}")
        result += ref_entry.html
        prev = new_pos
    result += convert_inline(new_mdx_text[prev:])       # 마지막 조각

    return f'<p>{result}</p>'
```

#### 명시적 실패 케이스

| 케이스 | 동작 |
|--------|------|
| `old_text != TextSegment 연결` | `SidecarMismatchError` — sidecar 재생성 후 testcase 업데이트 |
| `AnchorSegment ref`가 `sidecar_index`에 없음 | `SidecarMismatchError` — sidecar 구조 오류 |
| 삭제 구간 안에 `AnchorSegment` | `new_ptr`(삭제 직후) 로 매핑 (정의된 동작) |
| children이 없는 paragraph | 기존 경로 — `convert_inline(new_mdx_text)` 그대로 사용 |

실패가 발생하면:
1. 실패 케이스를 재현하는 testcase fixture를 추가한다
2. `SidecarMismatchError`면 sidecar 생성 로직을 수정하고 fixture를 재생성한다
3. 정의되지 않은 구조적 케이스면 설계를 보완하고 다시 사이클을 돈다

---

> **TODO — 구현 전 조사 필요**
>
> 1. **[확정] `myers_diff()` 좌표 단위**: Python str index (Unicode code point) 단위로 확정. 함수 시그니처 주석에 명시됨. 이모지 결합 문자 등 edge case는 발생 시 testcase 추가 대응.
>
> 2. **[Phase 1 선결] `old_mdx_text` 추출 방법**: `patch_builder.py`에서 paragraph 블록의 old MDX 텍스트를 어떻게 가져오는지 확인. `block_diff.py`의 `Change.old_block.content`가 이 역할을 하는지 확인.
>
> 3. **[Phase 1 선결] `<ac:image>`의 위치 유형 구분**: `<p>` 내부 inline vs `<p>` 외부 독립 block 케이스를 `mapping_recorder.py`가 어떻게 구분하는지 확인. 독립 block이면 이 설계 대상 밖.
>
> 4. **[확정] `convert_inline()` 적용 시점**: MDX 좌표로 MDX 텍스트를 먼저 분할한 뒤 각 조각에 `convert_inline()` 적용 — 좌표계 불일치 구조적 해소. `reconstruct_paragraph()` 구현에 반영됨.

---

### 3.2 문제 B 해결: Callout 내부 재귀 파싱

#### 아이디어

`_convert_callout_inner()`에서 내부 텍스트를 paragraph로 변환하는 대신, `parse_mdx_blocks()`로 내부를 블록 시퀀스로 파싱한 뒤 `mdx_block_to_xhtml_element()`를 재귀 적용한다.

#### 구현

```python
def _convert_callout_inner_full(text: str) -> str:
    """callout 내부를 재귀적으로 블록 파싱하여 XHTML을 재구성한다."""
    from mdx_to_storage.parser import parse_mdx_blocks

    # <Callout> 래퍼 제거 후 들여쓰기 보정
    inner = _strip_callout_wrapper(text)
    inner = _dedent_callout_body(inner)

    # 내부를 MDX 블록으로 파싱 (이미 존재하는 파서 재사용)
    inner_blocks = [b for b in parse_mdx_blocks(inner)
                    if b.type not in ('frontmatter', 'import_statement', 'empty')]

    if not inner_blocks:
        return ''

    # 각 블록을 재귀 재구성
    parts = [mdx_block_to_xhtml_element(b) for b in inner_blocks]
    return ''.join(parts)


def _dedent_callout_body(text: str) -> str:
    """callout 내부 들여쓰기(공통 선행 공백)를 제거한다."""
    lines = text.splitlines()
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return text
    indent = min(len(l) - len(l.lstrip()) for l in non_empty)
    return '\n'.join(l[indent:] for l in lines)
```

#### Callout 외부 wrapper: sidecar xhtml_type 활용

callout을 재구성할 때 원래 macro 포맷(`ac:structured-macro` vs `ac:adf-extension`)을 유지해야 한다. `sidecar_entry.xhtml_type`이 이미 이 정보를 갖고 있다.

```python
def mdx_callout_to_xhtml(block, sidecar_entry) -> str:
    """MDX callout 블록을 XHTML macro로 재구성한다."""
    callout_type = _extract_callout_type(block.content)   # "info" | "warning" | ...
    inner_xhtml = _convert_callout_inner_full(block.content)

    if sidecar_entry and sidecar_entry.xhtml_type == 'adf_extension':
        return _wrap_adf_callout(inner_xhtml, callout_type)
    else:
        return _wrap_structured_macro_callout(inner_xhtml, callout_type)
```

#### 재귀 파싱의 안전성

`parse_mdx_blocks()`는 현재 최상위 MDX 문서를 대상으로 작성되어 있다. callout 내부에 적용할 때 주의할 점:

- frontmatter, import_statement는 callout 내부에 없으므로 무시해도 됨 (이미 필터 적용)
- callout 내부에 다시 `<Callout>`이 있는 중첩 케이스: `mdx_block_to_xhtml_element()`의 callout 분기가 재귀 호출됨 → 자연스럽게 처리됨
- callout 내부의 `<figure>`, `<details>`, `<Badge>` 등 HTML 블록: `html_block` 타입으로 파싱되어 그대로 통과됨 → 문제 없음

---

## 4. 새로운 Reverse Sync 흐름

두 가지 문제가 해결되면 `build_patches()`의 로직이 다음과 같이 단순해진다.

### 4.1 변경된 블록 처리 (수정)

```
[현재]
modified 블록
  → _resolve_mapping_for_change() (6단계 폴백)
    → strategy: direct | containing | list | table | skip
      → (각 strategy마다 별도 처리)

[제안]
modified 블록
  → sidecar O(1) 조회 → BlockMapping
  → mdx_block_to_xhtml_element(new_block, sidecar_entry)
    → heading, paragraph, code_block: 직접 재구성
    → list: reconstruct_ul_entry() (trailing_html 재주입 포함)
    → callout: mdx_callout_to_xhtml() (재귀 파싱 + macro wrap)
    → 그 외: 기존 폴백
  → xhtml_xpath에 new_inner_xhtml 교체
```

### 4.2 삭제되는 코드

| 모듈/함수 | 이유 |
|-----------|------|
| `_resolve_mapping_for_change()` | 단순 sidecar O(1) 조회로 대체 |
| `_find_containing_mapping()` | containing 전략 불필요 |
| `_resolve_child_mapping()` 4단계 폴백 | sidecar가 정확하면 불필요 |
| `text_transfer.py` (대부분) | 텍스트 위치 매핑 불필요 |
| `has_inline_format_change()` | 재구성이 기본이므로 감지 불필요 |
| `has_inline_boundary_change()` | 동상 |
| `lost_info_patcher.py` 블록 레벨 heuristic | `inline_trailing_html` 재주입으로 대체 |
| `build_list_item_patches()` 매칭 로직 | `reconstruct_entry()` ref 순회로 대체 |
| `_convert_callout_inner()` → paragraph 폴백 | 재귀 파싱으로 대체 |

### 4.3 유지되는 코드

| 모듈/함수 | 이유 |
|-----------|------|
| `block_diff.py` | diff 로직 그대로 사용 |
| `sidecar.py` O(1) 인덱스 | 그대로 사용 (children/plain_text/inline_trailing_html 필드 추가) |
| `mdx_to_xhtml_inline.py` | 재구성의 핵심 — 확장 |
| `xhtml_patcher.py` `_replace_inner_html()` | XHTML 교체 메커니즘 |
| `roundtrip_verifier.py` | 검증 로직 |
| `table_patcher.py` | 테이블은 별도 처리 (표 구조가 복잡) |

---

## 5. 구현 계획

### Phase 1: Sidecar 플랫 매핑 + children ref 구조 도입

**목표:** `ul`/`ol`/`li` 및 `<p>` 내 `ac:image`를 최상위 SidecarEntry로 생성하고, 관계를 `children: [ref]`로 표현

**작업:**
1. `SidecarEntry` dataclass에 `children`, `plain_text`, `inline_trailing_html` 필드 추가
   - `children: List[ChildRef]` — `{'ref': xhtml_xpath}` 목록 (ul→li, li→block child, p→ac:image)
   - `plain_text: str` — li entry의 MDX 항목 텍스트 (zip 매칭 키)
   - `inline_trailing_html: str` — `<p>` 직후 non-block lossy 요소 원본 HTML
2. `_process_element(elem, xpath)` 구현 — `ul`/`ol`/`li`를 최상위 entry로 재귀 생성
   - `xhtml_type`은 XHTML 태그명 그대로 (`ul`, `ol`, `li`)
   - `<li>` 내 block 요소(`<ul>`, `<ol>`, block macro) → 독립 entry + `children` ref
   - `<li>` 내 non-block lossy 요소(`<ac:image>` 등) → `inline_trailing_html`에 저장
3. `_process_paragraph(elem, xpath)` 구현 — `<p>` 내 `ac:image` 를 독립 entry + `children` ref로 생성
   - `ParagraphEditSequence` 구조(`kind: text` / `kind: ref`) sidecar에 기록
4. `generate_sidecar_mapping()`의 list/paragraph 처리를 위 두 함수 호출로 교체
5. `load_sidecar_mapping()`에서 `children`, `plain_text`, `inline_trailing_html` 역직렬화
6. `mapping.yaml` 스키마 버전 업 (`version: 2`)

**검증 testcase:**

| testcase ID | 검증 대상 | 근거 |
|-------------|-----------|------|
| `544145591` | `ac:image` 포함 li 9개, nested list 21개 | li+image, nested 모두 풍부 |
| `880181257` | `ac:image` 포함 li 12개 | ac:image 포함 li 집중 검증 |
| `883654669` | `ac:image` 포함 li 16개 | ac:image 포함 li 최다 |

> **TODO:** Phase 1 시작 전 "TODO — 구현 전 조사 필요" 항목(Section 3.1) 중 1~5번 확인 후 구현 방향 확정

---

### Phase 2: `_convert_callout_inner` 재귀 파싱

**목표:** callout 내부 리스트/코드 블록을 올바르게 재구성

**작업:**
1. `_strip_callout_wrapper()` 및 `_dedent_callout_body()` 유틸리티 추가
2. `_convert_callout_inner_full()` 구현 (재귀 파싱)
3. `mdx_block_to_xhtml_element()`의 callout 분기에서 sidecar_entry를 인자로 받아 macro 포맷 결정
4. `mdx_block_to_xhtml_element()` 시그니처에 optional `sidecar_entry` 추가

**검증 testcase:**

| testcase ID | 검증 대상 | 근거 |
|-------------|-----------|------|
| `1454342158` | callout 내부 list 4개 | callout+list 가장 많음 |
| `880181257` | callout 내부 list 2개 | Phase 1+2 복합 케이스 (ac:image 포함 li도 존재) |

---

### Phase 3: `build_patches()` 재구성 경로 전환

**목표:** modified 블록 처리를 재구성 기반으로 전환

**작업:**
1. `reconstruct_ul_entry()` / `reconstruct_li_entry()` 구현 및 단위 테스트
2. `build_patches()`에서 modified 블록의 처리를 `mdx_block_to_xhtml_element()` 기반으로 전환
3. 기존 전략 분기(containing, list, text_transfer) 단계적 제거
4. 전체 테스트 케이스 통과 확인 (`make test-reverse-sync`)

**검증 기준:** `tests/reverse-sync/pages.yaml`의 모든 `expected_status: pass` 케이스 유지

---

## 6. 위험 및 대응

### 위험 1: inline 항목 텍스트 변경으로 `inline_trailing_html` 매칭 실패

**증상:** 리스트 항목 내용이 크게 바뀌면 `plain_text` 키가 일치하지 않아 `inline_trailing_html`을 찾지 못함

**대응:**
- `_match_mdx_inline_item()`에서 순서(index) 기반 폴백 우선 사용
  - `list_items` 시퀀스에서 `kind: inline` 항목의 순서(inline_ptr)와 MDX 항목의 순서를 매칭
  - 텍스트 완전 일치 → prefix 20자 매칭 → 순서 기반 매칭 순으로 폴백
- 매칭 실패 시 `inline_trailing_html` 없이 재구성 → lossy 요소 손실이지만 구조 파괴보다 안전

> **TODO (W-3):** prefix 20자 매칭의 충돌 가능성을 기존 testcase 전수 조사로 확인. 충돌이 빈번하면 prefix 폴백을 제거하고 순서 기반만 유지하는 방향 검토.

### 위험 2: Callout 내부 들여쓰기 처리 오류

**증상:** `_dedent_callout_body()`가 내부 코드 블록의 들여쓰기를 과도하게 제거

**대응:**
- code_block 내부는 `parse_mdx_blocks()`가 펜스 마커 기준으로 파싱하므로, 들여쓰기 제거가 코드 내용에 영향 없음
- 단위 테스트로 코드 블록 포함 callout 케이스 커버

### 위험 3: Sidecar 버전 비호환

**증상:** `list_items` 필드가 없는 구 버전 `mapping.yaml`을 읽을 때 오류

**대응:**
- `list_items`를 optional 필드로 선언 (기본값 `[]`)
- 구 버전 sidecar에서 `list_items`가 없으면 trailing 없이 재구성 → 기존 동작과 동일

---

## 7. 기대 효과 요약

| 지표 | 현재 | 개선 후 |
|------|------|---------|
| `patch_builder.py` 전략 수 | 5 (direct / containing / list / table / skip) | 2 (reconstruct / skip) |
| `_resolve_child_mapping()` 폴백 단계 | 4 | 0 (삭제) |
| 인라인 변경 감지 함수 | 2 (`has_inline_format_change`, `has_inline_boundary_change`) | 0 (삭제) |
| callout 내부 리스트 처리 | text_transfer 우회 | 재귀 재구성 |
| 신규 edge case 시 대응 | 전략 분기 추가 | `mdx_to_xhtml_inline.py` 개선 |
| 기술부채 방향 | 분기 누적 | 단일 재구성 경로 개선으로 집중 |

---

## 8. 테스트 설계

### 8.1 테스트 목표: 재구성의 "완전함"을 증명하는 방법

"완전함"을 다음 두 가지 명제로 구분하여 증명한다.

**명제 1 — 재구성 정확성:** `mdx_block_to_xhtml_element(block)`이 각 블록 타입에 대해 XHTML을 올바르게 생성한다.

**명제 2 — 손실 복원 완전성:** `trailing_html` 재주입 후 재구성된 XHTML이 원본 `page.xhtml`과 블록 수준에서 등가이다.

두 명제 모두 기존 `tests/testcases/`와 `tests/reverse-sync/`의 데이터로 검증할 수 있다. **새로운 테스트 입력 파일을 만들 필요가 없다.**

---

### 8.2 테스트 가능성 분류: 블록 타입별 재구성 가능성

주어진 testcase 내의 블록을 재구성 가능성에 따라 세 범주로 나눈다.

| 범주 | 설명 | 재구성 후 기대 결과 | 예시 |
|------|------|---------------------|------|
| **가역 블록** | MDX로 완전히 표현 가능한 블록 | 원본 XHTML과 byte-equal | heading, paragraph, code_block, 단순 list |
| **손실 복원 블록** | MDX에 표현 안 되는 요소가 있지만 trailing_html로 복원 가능 | trailing_html 포함 시 원본과 등가 | `<ac:image>` 포함 list item, `<span style>` 포함 항목 |
| **비가역 블록** | 정보 손실이 불가역적 | 기능적으로 무해한 변환만 허용 | `ac:adf-extension` callout, `ac:link` 포함 paragraph |

비가역 블록은 이미 `architecture.md`의 "정보 손실 카테고리"에 문서화된 항목들이다. 이 범주는 재구성 목표 밖이며, 테스트에서 skip 처리한다.

---

### 8.3 테스트 수준 구조 (5단계)

```
Level 0: 보조 함수 단위 테스트              (unit)
    ↓
Level 1: 블록 단위 재구성 정확성            (unit)
    ↓
Level 2: 전체 문서 재구성 + block-level 비교  (integration)
    ↓
Level 3: lossy 요소 재주입 후 byte-equal    (integration)
    ↓
Level 4: E2E reverse-sync 회귀 방지         (e2e)
```

---

### 8.3.1 Level 0: 보조 함수 단위 테스트

**목적:** 신규 추가되는 보조 함수 각각이 독립적으로 올바르게 동작하는지 확인한다. Level 1보다 먼저 실행하여 버그 위치를 좁힌다.

**실행 방법:**
```bash
python3 -m pytest tests/test_reconstruction_helpers.py -v --tb=short
```

#### 테스트 대상 함수 및 케이스

**`_process_element(ul_or_ol, xpath)`** — sidecar entry 생성

| 테스트 케이스 | 검증 내용 |
|---------------|-----------|
| 단순 `<ul><li><p>text</p></li></ul>` | `xhtml_type: ul` entry + `xhtml_type: li` entry 생성, children ref 정확성 |
| `<li>` 내부 `<ac:image>` 포함 | `inline_trailing_html` 추출, block child가 아님을 확인 |
| `<li>` 내부 nested `<ul>` | 부모 li의 `children`에 ref, nested ul의 독립 entry 생성 (`xhtml_type: ul`) |
| 빈 `<li>` (`<li></li>`) | `plain_text=""`, `children=[]` |
| `<li>` 내부 block macro (`<ac:structured-macro>`) | `children`에 ref, 독립 entry 생성 |
| `<ol>` | `xhtml_type: ol`로 생성 확인 |

**`map_anchor_positions(old_text, new_text, old_positions)`** — AnchorSegment 위치 매핑

| 테스트 케이스 | 검증 내용 |
|---------------|-----------|
| `old_text == new_text` | 모든 AnchorSegment position 그대로 유지 |
| 앞부분 삽입 (`"AB"` → `"XAB"`) | position이 삽입 길이만큼 뒤로 이동 |
| 앞부분 삭제 (`"AB"` → `"B"`) | position이 삭제 길이만큼 앞으로 이동 |
| 삭제 구간 안에 AnchorSegment (`"AB"` → `"B"`, position=1) | 삭제 직후 위치(0)로 매핑 |
| 전체 교체 | AnchorSegment가 new_text 끝으로 매핑 |
| AnchorSegment 2개, 중간 TextSegment 수정 | 각각 독립적으로 정확히 매핑 |

**`reconstruct_paragraph(old_mdx_text, new_mdx_text, entry, sidecar_index)`**

| 테스트 케이스 | 검증 내용 |
|---------------|-----------|
| `children` 없음 | `convert_inline(new_mdx_text)` 그대로 반환 |
| `old_mdx_text != TextSegment 연결` | `SidecarMismatchError` 발생 |
| AnchorSegment 1개, 텍스트 변경 없음 | AnchorSegment가 정확한 위치에 삽입 |
| AnchorSegment 2개, TextSegment 수정 | Myers diff로 두 AnchorSegment 위치 모두 정확히 매핑 |
| ref가 `sidecar_index`에 없음 | `SidecarMismatchError` 발생 |

**`_process_paragraph(elem, xpath)`** — ParagraphEditSequence sidecar entry 생성

| 테스트 케이스 | 검증 내용 |
|---------------|-----------|
| `<p>text only</p>` | `children = [{'kind': 'text', 'text': 'text only'}]` — TextSegment 1개 |
| `<p><strong>bold</strong></p>` | `children = [{'kind': 'text', 'text': 'bold'}]` — TextSegment 1개 (inline element는 get_text() 처리) |
| `<p>텍스트A <ac:image/> 텍스트B</p>` | `children = [text, ref, text]` 교차 시퀀스, `ac:image` 독립 entry 생성 |
| `<p><ac:image/><ac:image/></p>` | `children = [text(''), ref, text(''), ref, text('')]` — 빈 TextSegment 포함 |
| `<p>텍스트A <ac:image/></p>` | `children = [text, ref, text('')]` — 마지막 빈 TextSegment 포함 |

**`reconstruct_ul_entry(entry, sidecar_index, mdx_nodes)`** — ul/ol 재구성

| 테스트 케이스 | 검증 내용 |
|---------------|-----------|
| 단순 ul (sidecar 2개, mdx 2개 항목) | `<ul><li>...</li><li>...</li></ul>` 정상 재구성 |
| ol 재구성 | `xhtml_type: ol` → `<ol>` 출력 |
| sidecar 2개, mdx 3개 (항목 추가) | 새 항목이 `<li><p>...</p></li>` 로 출력에 포함 |
| sidecar 3개, mdx 2개 (항목 삭제) | 삭제 항목 생략, 2개 `<li>` 출력 |
| nested ul (li → ul → li 2단계) | 재귀 재구성 정확성 — `<ul><li><p>...</p><ul><li>...</li></ul></li></ul>` |

**`reconstruct_li_entry(entry, sidecar_index, node)`** — li 재구성

| 테스트 케이스 | 검증 내용 |
|---------------|-----------|
| 단순 li (텍스트만) | `<li><p>텍스트</p></li>` |
| `inline_trailing_html` 있는 li | `<li><p>텍스트</p><ac:image.../></li>` — trailing html 재주입 확인 |
| nested ul children 있는 li | `<li><p>텍스트</p><ul>...</ul></li>` |
| block macro children 있는 li | `xhtml_fragment` 그대로 삽입 |

**`normalize_xhtml(xhtml)`**

| 테스트 케이스 | 검증 내용 |
|---------------|-----------|
| 속성 순서 다른 두 XHTML | normalize 후 equal |
| `<br/>` vs `<br />` | normalize 후 equal |
| `<tag />` vs `<tag></tag>` (빈 속성값) | normalize 후 equal |
| trailing 공백 다른 텍스트 노드 | normalize 후에도 **not equal** |
| 다른 namespace prefix | normalize 후에도 **not equal** |

**`_strip_callout_wrapper(text)` / `_dedent_callout_body(text)`**

| 테스트 케이스 | 검증 내용 |
|---------------|-----------|
| `<Callout type="info">...</Callout>` | wrapper 제거 후 내부 텍스트만 반환 |
| 들여쓰기 2칸 callout body | 공통 선행 공백 제거 |
| 내부 코드 블록 포함 | 코드 블록 내 들여쓰기 보존 |

---

### 8.4 Level 1: 블록 단위 재구성 정확성 테스트

**목적:** `mdx_block_to_xhtml_element()`이 각 블록 타입에 대해 올바른 XHTML을 생성하는지 확인한다.

**데이터 소스:** `tests/testcases/{page_id}/mapping.yaml` + `expected.mdx`

**방법:**

`mapping.yaml`은 각 MDX 블록의 `xhtml_xpath`와 원본 XHTML 내 `xhtml_text`를 갖고 있다. `expected.mdx`를 파싱하여 각 블록을 재구성하면, `mapping.yaml`의 `xhtml_text`와 비교할 수 있다.

```python
# tests/test_reconstruction_unit.py

def test_block_reconstruction(page_id, block_idx):
    """각 MDX 블록을 재구성하여 원본 XHTML 텍스트와 비교한다."""
    mapping = load_mapping(f"testcases/{page_id}/mapping.yaml")
    mdx_blocks = parse_mdx_blocks(open(f"testcases/{page_id}/expected.mdx").read())

    for entry in mapping.entries:
        mdx_idx = entry.mdx_blocks[0] if entry.mdx_blocks else None
        if mdx_idx is None:
            continue  # 비가역 블록 skip

        block = mdx_blocks[mdx_idx]
        reconstructed = mdx_block_to_xhtml_element(block)

        # normalize_xhtml() 정규화 범위:
        #   정규화 O — 속성 순서, 빈 태그 형식(<br/> vs <br />), 빈 속성값 형식
        #   정규화 X — 텍스트 노드 trailing 공백, 네임스페이스 prefix
        # trailing 공백 차이나 namespace prefix 차이는 실제 버그로 판정한다.
        assert normalize_xhtml(reconstructed) == normalize_xhtml(entry.xhtml_text), \
            f"Block {block_idx} ({block.type}) mismatch"
```

#### `normalize_xhtml()` 스펙

| 항목 | 정규화 여부 | 이유 |
|------|------------|------|
| 속성 순서 | ✅ 정렬 | `mdx_block_to_xhtml_element()` 출력 순서가 원본과 다를 수 있음 |
| 빈 태그 형식 (`<br/>` vs `<br />`) | ✅ 통일 | XML 파서/직렬화 도구마다 출력이 다름 |
| 빈 속성값 형식 (`<ac:parameter ... />` vs `<ac:parameter ...></ac:parameter>`) | ✅ 통일 | BeautifulSoup 출력 방식에 따라 달라짐 |
| 텍스트 노드 trailing 공백 | ❌ 유지 | 공백 차이는 실제 버그로 판정 |
| 네임스페이스 prefix (`ac:`, `ri:`) | ❌ 유지 | prefix는 항상 동일하게 유지되어야 함 — 차이 발생 시 실제 버그 |

```python
def normalize_xhtml(xhtml: str) -> str:
    """비교용 XHTML 정규화.

    정규화 O: 속성 순서, 빈 태그 형식, 빈 속성값 형식
    정규화 X: 텍스트 노드 공백, 네임스페이스 prefix
    """
    from lxml import etree
    root = etree.fromstring(f"<root>{xhtml}</root>")
    for elem in root.iter():
        # 속성 순서 정렬
        elem.attrib = dict(sorted(elem.attrib.items()))
    # 직렬화 — 빈 태그/속성값 형식은 lxml 기본 출력으로 통일
    result = etree.tostring(root, encoding="unicode")
    # <root>...</root> 제거
    return result[6:-7]
```

이 함수 자체에 대한 단위 테스트(Level 0)가 필요하다 — Section 8.3 Level 0 참고.

**측정 지표:** `passed_blocks / total_blocks` — 목표 80% 이상 (비가역 블록 제외)

**실행 방법:**
```bash
python3 -m pytest tests/test_reconstruction_unit.py -v \
    --tb=short --no-header 2>&1 | tail -20
```

---

### 8.5 Level 2: 전체 문서 재구성 커버리지 테스트

**목적:** `tests/testcases/`의 모든 페이지에 대해 재구성이 가능한 블록의 비율(커버리지)을 측정한다.

**방법:** 각 페이지의 `expected.mdx`를 전체 재구성한 뒤, 원본 `page.xhtml`의 beautified diff와 비교한다. 비가역 블록 위치에서 발생하는 diff만 허용한다.

```
tests/testcases/{page_id}/
    page.xhtml                ← 원본
    expected.mdx              ← MDX 입력
    mapping.yaml              ← 블록 매핑
    output.reconstruct.xhtml  ← 재구성 결과 (신규 생성)
    output.reconstruct.diff   ← beautify-diff (신규 생성)
```

#### 핵심 함수 인터페이스

```python
def reconstruct_full_xhtml(
    mdx_text: str,
    mapping: SidecarMapping,
    page_xhtml: str,              # 비가역 블록 원본 보존용
) -> str:
    """MDX 전체를 sidecar mapping 기반으로 재구성한다.

    처리 순서:
      1. mapping의 각 entry를 순회
      2. 가역 블록 → mdx_block_to_xhtml_element()로 재구성
      3. 비가역 블록(ac:link 포함, adf_extension 등) → page_xhtml에서 원본 fragment 추출하여 그대로 사용
      4. document envelope(prefix/suffix) → sidecar에서 복원 (RoundtripSidecar.reassemble_xhtml() 참고)
    """


def compare_reversible_blocks(
    original: str,
    reconstructed: str,
    mapping: SidecarMapping,
) -> list[str]:
    """가역 블록에서 발생한 diff 목록을 반환한다.

    반환값이 [] 이면 전원 일치.
    mapping의 각 entry를 순회하며:
      - 비가역 블록(ac:link 포함, adf_extension 등) → skip
      - 가역 블록 → original vs reconstructed의 해당 xhtml_xpath fragment 비교
      - 불일치 시 f"{xhtml_xpath}: {diff}" 형태의 문자열을 목록에 추가
    normalize_xhtml()로 정규화 후 비교한다.
    """
```

**실행 스크립트 (기존 run-tests.sh 확장):**

```bash
# run-tests.sh에 추가할 타입
# --type reconstruct
# page.xhtml의 모든 블록을 expected.mdx로 재구성하여 diff를 생성한다.
```

```python
# tests/test_reconstruction_coverage.py

@pytest.mark.parametrize("page_id", list_testcase_ids())
def test_reconstruction_coverage(page_id):
    """MDX → XHTML 재구성 커버리지: 가역 블록은 원본과 일치해야 한다."""
    page_xhtml = open(f"testcases/{page_id}/page.xhtml").read()
    mdx_text = open(f"testcases/{page_id}/expected.mdx").read()
    mapping = load_mapping(f"testcases/{page_id}/mapping.yaml")

    reconstructed_xhtml = reconstruct_full_xhtml(mdx_text, mapping, page_xhtml)

    reversible_diffs = compare_reversible_blocks(
        original=page_xhtml,
        reconstructed=reconstructed_xhtml,
        mapping=mapping,
    )
    # 가역 블록에서 diff가 없어야 함
    assert reversible_diffs == [], \
        f"Reversible block diff found:\n" + "\n".join(reversible_diffs)
```

**`compare_reversible_blocks()`의 동작:**

1. `mapping.yaml`의 각 엔트리를 순회
2. 비가역 블록(ac:link 포함, adf_extension 등) → skip
3. 가역 블록 → `original_block_xhtml` vs `reconstructed_block_xhtml` 비교
4. 불일치 시 diff를 반환

---

### 8.6 Level 3: 재구성 후 byte-equal 테스트

**목적:** 손실 복원 블록(`ac:image`, `inline_trailing_html` 포함 항목 등)에 대해 재구성 결과가 원본 XHTML fragment와 byte-equal임을 증명한다.

#### 기존 인프라 (신규 파일 불필요)

다음 구현이 이미 존재한다:

| 항목 | 구현 위치 | 설명 |
|------|-----------|------|
| `expected.roundtrip.json` 파일 | `tests/testcases/{page_id}/` | `SidecarBlock.xhtml_fragment` (byte-exact), `SidecarBlock.mdx_content_hash` (SHA-256) 포함 |
| `SidecarBlock.mdx_content_hash` | `bin/reverse_sync/sidecar.py` L53 | MDX 블록 content의 SHA-256 — MDX 블록 식별 키 |
| `RoundtripSidecar`, `load_sidecar()` | `bin/reverse_sync/sidecar.py` L59, L233 | JSON 역직렬화 |
| `build_sidecar()` | `bin/reverse_sync/sidecar.py` L159 | `page.xhtml` + `expected.mdx` → `RoundtripSidecar` 생성 |
| 생성 CLI | `bin/mdx_to_storage_roundtrip_sidecar_cli.py` | `batch-generate` 서브커맨드로 전체 testcase 일괄 생성 |
| splice 경로 | `bin/reverse_sync/rehydrator.py` L62 `splice_rehydrate_xhtml()` | `mdx_content_hash` 기반 블록 매칭 — `find_mdx_block_by_hash()` 역할 수행 |

**데이터 소스:** `tests/testcases/{page_id}/expected.roundtrip.json` + `tests/testcases/{page_id}/expected.mdx`

#### 테스트 코드

```python
# tests/test_reconstruction_lossless.py

from reverse_sync.sidecar import load_sidecar, sha256_text, load_sidecar_mapping
from reverse_sync.mdx_block_parser import parse_mdx_blocks

@pytest.mark.parametrize("page_id", list_testcase_ids())
def test_lossless_reconstruction(page_id):
    """재구성 결과가 원본 XHTML fragment와 byte-equal인지 검증한다."""
    sidecar = load_sidecar(Path(f"testcases/{page_id}/expected.roundtrip.json"))
    # load_sidecar: bin/reverse_sync/sidecar.py L233
    mapping_entries = load_sidecar_mapping(f"testcases/{page_id}/mapping.yaml")
    # load_sidecar_mapping: bin/reverse_sync/sidecar.py L257
    xpath_index = {e.xhtml_xpath: e for e in mapping_entries}

    mdx_text = open(f"testcases/{page_id}/expected.mdx").read()
    mdx_blocks = parse_mdx_blocks(mdx_text)
    # parse_mdx_blocks: bin/reverse_sync/mdx_block_parser.py

    # mdx_content_hash → MDX 블록 인덱스 (splice 경로와 동일 방식)
    # rehydrator.py L96: content_hash == sb.mdx_content_hash 비교와 동일
    hash_to_block = {sha256_text(b.content): b for b in mdx_blocks if b.content}

    for sb in sidecar.blocks:
        if not sb.mdx_content_hash:
            continue  # MDX 대응 없는 블록 skip (image, TOC 등)
            # SidecarBlock.mdx_content_hash: sidecar.py L53

        mdx_block = hash_to_block.get(sb.mdx_content_hash)
        if mdx_block is None:
            pytest.skip(f"hash not found: {sb.mdx_content_hash[:8]}...")

        sidecar_entry = xpath_index.get(sb.xhtml_xpath)
        reconstructed = mdx_block_to_xhtml_element(mdx_block, sidecar_entry)

        assert reconstructed == sb.xhtml_fragment, (
            f"Fragment mismatch at {sb.xhtml_xpath}:\n"
            f"  expected: {sb.xhtml_fragment!r}\n"
            f"  got:      {reconstructed!r}"
        )
```

#### 기존 `byte_verify`와의 관계

| 검증 | 구현 | 목적 |
|------|------|------|
| 기존 `byte_verify` | `bin/reverse_sync/byte_verify.py` | MDX 무변경 시 XHTML byte-equal 보장 (fast path) |
| Level 3 `test_reconstruction_lossless` | 신규 | 재구성 경로로 변환해도 byte-equal임을 보장 |

Level 3이 통과하면 "재구성 = fast path"임이 증명된다.

**측정 목표: failed = 0** (mdx_content_hash 없는 블록 skip 제외)

---

### 8.7 Level 4: E2E 회귀 방지 테스트

**목적:** 재구성 기반 reverse-sync가 기존 테스트케이스를 회귀시키지 않음을 보장한다.

**데이터 소스:** `tests/reverse-sync/{page_id}/` (기존 인프라 그대로 사용)

**방법:** 기존 `run-tests.sh --type reverse-sync-verify`를 그대로 사용하되, reverse-sync 내부 경로가 재구성 기반으로 전환된 후 동일하게 실행한다.

```bash
# 기존 명령 그대로
cd tests && ./run-tests.sh --type reverse-sync-verify

# 검증 기준: pages.yaml의 expected_status와 일치
# pass 26건 유지, fail 16건 유지 (신규 pass 전환만 허용)
```

**회귀 판정 기준:**

| 상태 전환 | 판정 |
|-----------|------|
| `pass` → `pass` | ✅ 유지 |
| `fail` → `pass` | ✅ 개선 (expected_status 업데이트 필요) |
| `pass` → `fail` | ❌ 회귀 — PR 차단 |
| `fail` → `fail` | ✅ 유지 |

**Phase 3 구현 완료 기준:** 26건 `expected_status: pass` 전원 유지 + 신규 pass 전환 확인

---

### 8.8 테스트 실행 순서와 피드백 루프

구현 변경 후 아래 순서로 테스트를 실행한다. 각 단계는 이전 단계가 전원 통과한 후 진행한다.

#### Step 1 — Level 1 실행

```bash
python3 -m pytest tests/test_reconstruction_unit.py -v --tb=short
```

**무엇을 확인하는가:** 블록 하나를 재구성했을 때 XHTML이 올바른가.

**실패 시 수정 위치:** `bin/reverse_sync/mdx_to_xhtml_inline.py` — 해당 블록 타입의 변환 로직.

---

#### Step 2 — Level 2 실행

```bash
python3 -m pytest tests/test_reconstruction_coverage.py -v --tb=short
```

**무엇을 확인하는가:** 문서 전체를 재구성했을 때 블록 조립 순서와 envelope(문서 앞뒤 고정 텍스트)가 올바른가.

**실패 시 수정 위치:** 블록 조립 순서 오류라면 `reconstruct_entry()`, envelope 오류라면 `RoundtripSidecar.reassemble_xhtml()` (`bin/reverse_sync/sidecar.py` L70).

---

#### Step 3 — Level 3 실행

```bash
python3 -m pytest tests/test_reconstruction_lossless.py -v --tb=short
```

**무엇을 확인하는가:** `ac:image` 등 lossy 요소를 재주입한 후 원본 XHTML fragment와 byte-equal인가.

**실패 시 수정 위치:** sidecar 생성 로직 — `_process_element()` 또는 `reconstruct_entry()`의 `inline_trailing_html` / `children ref` 처리.

---

#### Step 4 — Level 4 실행

```bash
cd tests && ./run-tests.sh --type reverse-sync-verify
```

**무엇을 확인하는가:** 기존에 통과하던 reverse-sync E2E 케이스가 재구성 경로 전환 후에도 동일하게 통과하는가.

**실패 시 수정 위치:** `bin/reverse_sync/patch_builder.py`의 재구성 경로 — Level 1/2/3에서 놓친 블록 타입이 있다는 신호이므로, 해당 케이스를 Level 1 단위 테스트로 먼저 재현하고 수정한다.

---

#### 판정 기준 요약

| 단계 | 통과 기준 | 실패 의미 |
|------|-----------|-----------|
| Level 1 | 모든 블록 타입 재구성 정확 | 변환 로직 버그 |
| Level 2 | 문서 단위 조립 정확 | 블록 순서 또는 envelope 버그 |
| Level 3 | lossy 요소 재주입 후 byte-equal | sidecar children/trailing 추출 버그 |
| Level 4 | 기존 pass 케이스 전원 유지 | Level 1~3에서 놓친 케이스 존재 |

---

### 8.9 기존 인프라와의 관계 정리

| 기존 테스트 | 역할 | 재구성 후 변화 |
|-------------|------|----------------|
| `run-tests.sh --type convert` | XHTML → MDX forward 변환 검증 | 변화 없음 |
| `run-tests.sh --type reverse-sync` | expected 파일 비교 | Phase 3 완료 후 expected 파일 재생성 필요 |
| `run-tests.sh --type reverse-sync-verify` | `expected_status` 검증 | 그대로 사용 (회귀 게이트) |
| `byte_verify` | roundtrip sidecar byte-equal | 변화 없음 (fast path 그대로) |
| `test_reconstruction_unit.py` | **신규** — 블록 단위 재구성 | Level 1 |
| `test_reconstruction_lossless.py` | **신규** — trailing_html byte-equal | Level 3 |
