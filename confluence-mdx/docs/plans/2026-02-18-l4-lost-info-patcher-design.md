# Phase L4: 메타데이터 활용 패처 설계

## 목표

L3에서 수집한 `lost_info`(emoticon, link, filename, adf_extension)를 활용하여, 변경된 블록의 emitter 출력을 원본에 가까운 XHTML로 후처리한다.

## 배경

L3에서 정순변환 시 손실되는 4가지 비가역 정보를 mapping.yaml의 페이지 레벨 `lost_info`에 기록하였다. 현재 이 정보는 어디에서도 활용되지 않는다. Emitter 단독으로는 이 정보를 복원할 수 없으므로, emitter 출력을 lost_info로 후처리하는 패처가 필요하다.

## 적용 대상

| 경로 | 위치 | 상황 |
|------|------|------|
| Splice rehydration | `rehydrator.py` | 해시 불일치 블록 → `emit_single_block()` |
| Reverse sync insert | `patch_builder.py` | 추가 블록 → `mdx_block_to_xhtml_element()` |

## 설계

### 1. lost_info 블록 분배

페이지 레벨 lost_info를 각 sidecar 블록에 할당한다. 각 항목의 `raw` 필드가 블록의 `xhtml_fragment`에 포함되는지로 판별한다.

### 2. 독립 패처 모듈 (`reverse_sync/lost_info_patcher.py`)

`apply_lost_info(emitted_xhtml: str, lost_info: dict) -> str`

4가지 카테고리별 패치:

| 카테고리 | 매칭 기준 | 치환 |
|----------|----------|------|
| emoticons | Unicode emoji → `ac:name` 매핑 | `✔️` → `<ac:emoticon ac:name="tick"/>` |
| links | `href="#link-error"` | `<a>` → 원본 `<ac:link>` raw |
| filenames | normalized filename in `ri:filename` | normalized → original |
| adf_extensions | `<ac:structured-macro>` matching type | macro → 원본 `<ac:adf-extension>` raw |

### 3. 통합

- `splice_rehydrate_xhtml()`: `emit_single_block()` 후 `apply_lost_info()` 호출
- `_build_insert_patch()`: `mdx_block_to_xhtml_element()` 후 `apply_lost_info()` 호출

## 인수 기준

1. 변경되지 않은 블록: byte-equal 유지 (L2)
2. 변경된 블록: well-formed XHTML + lost_info 복원
3. 기존 테스트 전부 통과
4. lost_info_patcher 유닛 테스트 추가
