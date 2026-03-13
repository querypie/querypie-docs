# Reverse Sync 전면 재구성 설계 — 검토 평가 결과 (v4)

> 검토 대상: `2026-03-13-reverse-sync-reconstruction-design.md`
> 검토일: 2026-03-13
> 검토자: Claude Sonnet 4.6
> 이전 검토(v3) 대비 변경: 이전 지적사항 전체 반영 확인 + 신규 이슈 도출

---

## 이전 검토(v3) 반영 결과

| 항목 | 내용 | 반영 결과 |
|------|------|-----------|
| C-1 | Section 5 Phase 1이 v1 설계(`list_items` 중첩 필드)를 기술 | ✅ 플랫 매핑 + children ref 기준으로 재작성, `_process_paragraph()` 추가 |
| C-2 | `zip()` silent truncation — 항목 추가 시 새 항목 누락 | ✅ `for node in mdx_nodes[len(sidecar_refs):]` 후처리 루프 추가 |
| W-1 | ParagraphEditSequence 생성(sidecar creation) 로직 미정의 | ✅ `_process_paragraph()` 완전 정의 (XHTML 조각 누적 + `convert_inline()`) |
| W-2 | `reconstruct_ul/li_entry()` Level 0 테스트 미명시 | ✅ 각 함수별 테스트 케이스 추가 |
| W-3 | Section 4.1이 구 함수명 `reconstruct_list_with_trailing()` 참조 | ✅ `reconstruct_ul_entry()`로 교체 |
| S-1 | `<p>` 없는 `<li>` 처리 미명시 | ✅ Confluence에서 존재하지 않음을 코드 주석에 명시 |
| S-2 | 다단락 `<li>` 처리 미언급 | ✅ 존재 여부 조사 TODO 추가 (Section 3.1 TODO 6) |

이전 지적사항 7건 전부 반영되었습니다. 아래는 최신 설계 문서 기준 신규 이슈입니다.

---

## 총평

설계가 구현 가능한 수준에 도달했습니다. 플랫 sidecar + children ref, ParagraphEditSequence, 5단계 테스트 구조가 일관성을 갖추었고, `_process_paragraph()` 생성 측이 완전히 정의된 것이 특히 중요한 개선입니다.

남은 이슈는 Section 6가 이전 설계(v1)를 참조하는 불일치와, Level 0 테스트의 예상값 오류입니다.

---

## Warning — 구현 시 혼란을 유발할 수 있는 문제

### W-1. Section 6 위험 1이 삭제된 설계를 기술

**위치:** Section 6 위험 1

```
- _match_mdx_inline_item()에서 순서(index) 기반 폴백 우선 사용
  - list_items 시퀀스에서 kind: inline 항목의 순서(inline_ptr)와 MDX 항목의 순서를 매칭
  - 텍스트 완전 일치 → prefix 20자 매칭 → 순서 기반 매칭 순으로 폴백
```

현재 설계는 `_match_mdx_inline_item()`, `list_items` 필드, 텍스트 매칭을 사용하지 않습니다. `reconstruct_ul_entry()`의 `zip()` 위치 기반 매칭으로 전부 대체되었습니다. 위험 1의 "증상"(텍스트 변경으로 matching 실패)도 더 이상 발생하지 않습니다.

현재 설계에서 위험 1에 해당하는 실제 위험은 **sidecar 항목 수와 MDX 항목 수 불일치 시 `inline_trailing_html` 손실**이며, 이는 케이스 분류 표에 이미 기술되어 있습니다. Section 6 위험 1을 현재 설계 기준으로 교체해야 합니다.

---

### W-2. Section 6 위험 3이 삭제된 `list_items` 필드를 기술

**위치:** Section 6 위험 3

```
- list_items를 optional 필드로 선언 (기본값 [])
- 구 버전 sidecar에서 list_items가 없으면 trailing 없이 재구성 → 기존 동작과 동일
```

`list_items`는 v1 설계 필드로, 현재 설계에 없습니다. 실제 backward compat 대상은 `children`, `plain_text`, `inline_trailing_html`이며, `reconstruct_paragraph()`의 `if not entry.children` 폴백이 이를 처리합니다. Section 6 위험 3을 현재 스키마 기준으로 업데이트해야 합니다.

---

### W-3. `_process_paragraph()` Level 0 테스트 예상값 오류

**위치:** Section 8.3.1 Level 0 `_process_paragraph()` 테스트 케이스

```
| <p><strong>bold</strong></p> | children = [{'kind': 'text', 'text': 'bold'}]
                                 — TextSegment 1개 (inline element는 get_text() 처리) |
```

그러나 `_process_paragraph()` 구현은:

```python
cursor_xhtml += str(child)   # → "<strong>bold</strong>" 누적
children.append({'kind': 'text', 'text': convert_inline(cursor_xhtml)})
```

`convert_inline("<strong>bold</strong>")` = `"**bold**"` (MDX bold)이므로 TextSegment.text는 `'bold'`가 아니라 `'**bold**'`여야 합니다. 주석의 `inline element는 get_text() 처리`도 구현과 다릅니다.

설계 문서는 "TextSegment.text는 MDX 텍스트 조각"으로 명시하므로, 테스트 케이스 예상값을 `'**bold**'`로, 주석을 `XHTML 조각을 convert_inline()으로 변환`으로 수정해야 합니다.

---

## Suggestion

### S-1. Section 6 위험 1 TODO가 삭제된 설계를 참조

**위치:** Section 6 위험 1 하단

```
> TODO (W-3): prefix 20자 매칭의 충돌 가능성을 기존 testcase 전수 조사로 확인.
```

prefix 20자 매칭은 현재 설계에서 완전히 제거되었습니다. 이 TODO는 삭제하면 됩니다.

---

### S-2. Level 1 테스트가 sidecar-aware 경로를 커버하지 않음을 미명시

**위치:** Section 8.4 Level 1 테스트 코드

```python
reconstructed = mdx_block_to_xhtml_element(block)
```

`sidecar_entry` 없이 호출하므로 `inline_trailing_html` 재주입 경로와 callout macro 포맷 선택 경로가 Level 1에서 커버되지 않습니다. 이 경로들이 Level 3에서 검증되는 의도라면 Section 8.4에 명시하면 충분합니다:

> "sidecar-aware 경로(list `inline_trailing_html`, callout macro format)는 Level 3에서 검증한다."

---

## 평가 요약

| 항목 | 평가 |
|------|------|
| 이전 지적사항 전체 반영 | ✅ |
| 플랫 매핑 + children ref 구조 | ✅ |
| `_process_paragraph()` 생성 측 완전 정의 | ✅ |
| `zip()` 항목 추가 후처리 루프 | ✅ |
| 5단계 테스트 구조 및 실행 흐름 | ✅ |
| Level 0 `reconstruct_ul/li_entry()` + `_process_paragraph()` 테스트 | ✅ |
| Section 5 Phase 1 ↔ Section 3.1 일치 | ✅ |
| Section 6 위험 1 구 설계 기술 (W-1) | ⚠️ |
| Section 6 위험 3 `list_items` 참조 (W-2) | ⚠️ |
| `_process_paragraph()` Level 0 예상값 오류 (W-3) | ⚠️ |
| Section 6 위험 1 TODO 잔존 (S-1) | 💡 |
| Level 1 sidecar-aware 경로 미커버 미명시 (S-2) | 💡 |

---

## 다음 단계

Warning 3건(W-1~3)은 구현 전에 수정하는 것이 좋습니다.

- **W-1, W-2**: Section 6를 현재 설계 기준으로 재작성
- **W-3**: `_process_paragraph()` Level 0 테스트 예상값과 주석을 `str(child)` + `convert_inline()` 기준으로 수정
