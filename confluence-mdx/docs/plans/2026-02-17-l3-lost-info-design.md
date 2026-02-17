# Phase L3: Forward Conversion 정보 보존 (lost_info) 설계

## 목표

정순변환(Forward Conversion) 과정에서 손실되는 Confluence XHTML 정보를 `mapping.yaml`의 각 매핑 엔트리에 `lost_info` 필드로 기록한다. 이 정보는 이후 Phase L4에서 역순변환(Backward Conversion) 시 원본에 가까운 XHTML을 재생성하는 데 사용한다.

## 배경

현재 emitter 단독 검증(normalize-diff)은 21건 중 1건만 통과한다. 실패 원인 분포:

| 원인 | 건수 | 비가역 여부 |
|------|------|-------------|
| `attachment_filename_mismatch` | 9 | 비가역 — 정순변환에서 파일명 정규화 |
| `internal_link_unresolved` (`#link-error`) | 7 | 비가역 — 정순변환에서 원본 정보 소실 |
| `emoticon_representation_mismatch` | 4 | 비가역 — 정순변환에서 shortname 소실 |
| `adf_extension_panel_mismatch` | 3 | 비가역 — ADF 구조가 MDX에 없음 |

이 항목들은 emitter 개선만으로는 해결할 수 없다. 정순변환 시점에 원본 정보를 보존해야 한다.

## 현재 아키텍처

### 정보 손실 지점 (converter/core.py)

| 항목 | 위치 | 입력 XHTML | 출력 MDX | 손실 정보 |
|------|------|-----------|---------|----------|
| emoticon | `SingleLineParser.convert_recursively` (core.py:318-343) | `<ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:" .../>` | `✔️` | ac:name, ac:emoji-id, ac:emoji-shortname |
| link | `SingleLineParser.convert_ac_link` (core.py:491, context.py:413) | `<ac:link><ri:page ri:content-title="Missing Page"/>...</ac:link>` | `[Missing Page](#link-error)` | ri:content-title, ri:space-key, raw XHTML |
| filename | `Attachment.__init__` (core.py:57-61) | `ri:filename="스크린샷 2024-08-01 오후 2.50.06.png"` | `screenshot-20240801-145006.png` | 원본 파일명 |
| adf_extension | `AdfExtensionToCallout.convert_recursively` (core.py:1308-1349) | `<ac:adf-extension>...<ac:adf-fallback>...</ac:adf-fallback></ac:adf-extension>` | `<Callout type="important">...</Callout>` | adf-fallback, local-id, 전체 구조 |
| stripped_attrs | `get_html_attributes` (context.py:560-598) | style, class, ac:local-id, data-* | (제거됨) | 속성 값 |

### mapping.yaml 생성 흐름

PR #798에서 `converter/sidecar_mapping.py`가 삭제되고, `reverse_sync/sidecar.py`의 `generate_sidecar_mapping()`으로 통합되었다.

```
converter/cli.py
  └─ generate_sidecar_mapping(xhtml, mdx, page_id)  ← reverse_sync/sidecar.py
       ├─ record_mapping(xhtml) → List[BlockMapping]
       ├─ parse_mdx_blocks(mdx) → List[MdxBlock]
       └─ 텍스트 기반 매칭 → mapping.yaml 출력
```

### mapping.yaml 현재 스키마 (version 1)

```yaml
version: 1
source_page_id: "544381877"
mdx_file: "page.mdx"
mappings:
  - xhtml_xpath: "h2[1]"
    xhtml_type: "heading"
    mdx_blocks: [2]
  - xhtml_xpath: "p[1]"
    xhtml_type: "paragraph"
    mdx_blocks: [4]
```

## 설계

### 1. mapping.yaml 스키마 확장 (version 2)

각 mapping entry에 `lost_info` 필드를 추가한다. 손실 정보가 없는 블록은 필드를 생략한다.

```yaml
version: 2
source_page_id: "544381877"
mdx_file: "page.mdx"
mappings:
  - xhtml_xpath: "h2[1]"
    xhtml_type: "heading"
    mdx_blocks: [2]
    # lost_info 생략 — 손실 없음
  - xhtml_xpath: "p[3]"
    xhtml_type: "paragraph"
    mdx_blocks: [8]
    lost_info:
      emoticons:
        - name: "tick"
          shortname: ":check_mark:"
          emoji_id: "atlassian-check_mark"
          fallback: ":check_mark:"
          raw: '<ac:emoticon ac:name="tick" ac:emoji-shortname=":check_mark:" ac:emoji-id="atlassian-check_mark" ac:emoji-fallback=":check_mark:"/>'
      links:
        - content_title: "Missing Page"
          space_key: ""
          raw: '<ac:link><ri:page ri:content-title="Missing Page"/><ac:link-body>Missing Page</ac:link-body></ac:link>'
      filenames:
        - original: "스크린샷 2024-08-01 오후 2.50.06.png"
          normalized: "screenshot-20240801-145006.png"
      adf_extensions:
        - panel_type: "note"
          raw: '<ac:adf-extension>...</ac:adf-extension>'
      stripped_attrs:
        ac:macro-id: "a935cf67-ed54-4b6b-aafd-63cbebe654e1"
```

### 2. 수집 메커니즘

#### LostInfoCollector 클래스

`converter/core.py`에 블록 단위 수집기를 도입한다.

```python
class LostInfoCollector:
    """현재 블록 변환 중 손실되는 정보를 수집한다."""

    def __init__(self):
        self._emoticons: list[dict] = []
        self._links: list[dict] = []
        self._filenames: list[dict] = []
        self._adf_extensions: list[dict] = []
        self._stripped_attrs: dict[str, str] = {}

    def add_emoticon(self, node: Tag) -> None:
        self._emoticons.append({
            "name": node.get("ac:name", ""),
            "shortname": node.get("ac:emoji-shortname", ""),
            "emoji_id": node.get("ac:emoji-id", ""),
            "fallback": node.get("ac:emoji-fallback", ""),
            "raw": str(node),
        })

    def add_link(self, node: Tag) -> None:
        ri_page = node.find("ri:page")
        self._links.append({
            "content_title": ri_page.get("ri:content-title", "") if ri_page else "",
            "space_key": ri_page.get("ri:space-key", "") if ri_page else "",
            "raw": str(node),
        })

    def add_filename(self, original: str, normalized: str) -> None:
        if original != normalized:
            self._filenames.append({
                "original": original,
                "normalized": normalized,
            })

    def add_adf_extension(self, node: Tag, panel_type: str) -> None:
        self._adf_extensions.append({
            "panel_type": panel_type,
            "raw": str(node),
        })

    def add_stripped_attr(self, name: str, value: str) -> None:
        self._stripped_attrs[name] = value

    def to_dict(self) -> dict:
        """빈 카테고리를 제외하고 반환한다."""
        result = {}
        if self._emoticons:
            result["emoticons"] = self._emoticons
        if self._links:
            result["links"] = self._links
        if self._filenames:
            result["filenames"] = self._filenames
        if self._adf_extensions:
            result["adf_extensions"] = self._adf_extensions
        if self._stripped_attrs:
            result["stripped_attrs"] = self._stripped_attrs
        return result
```

#### 수집 지점

| 수집 지점 | 트리거 조건 | 수집 메서드 |
|----------|-----------|-----------|
| `SingleLineParser` ac:emoticon 분기 (core.py:318) | 항상 | `collector.add_emoticon(node)` |
| `SingleLineParser.convert_ac_link` (core.py:491, context.py:413) | `href == '#link-error'` | `collector.add_link(node)` |
| `Attachment.__init__` (core.py:57-61) | `original != normalized` | `collector.add_filename(original, normalized)` |
| `AdfExtensionToCallout` (core.py:1317-1349) | 항상 | `collector.add_adf_extension(node, panel_type)` |
| `get_html_attributes` (context.py:572-581) | 제거 시 | `collector.add_stripped_attr(name, value)` |

#### collector 전달 경로

```
ConfluenceToMarkdown.as_markdown()
  └─ MultiLineParser(soup)
       ├─ 블록 진입 시: collector = LostInfoCollector()
       ├─ SingleLineParser(node, collector=collector)
       ├─ AdfExtensionToCallout(node, collector=collector)
       ├─ 블록 완료 시: block_lost_infos[block_index] = collector.to_dict()
       └─ 전체 완료 시: self.lost_infos = block_lost_infos
```

`ConfluenceToMarkdown`이 수집 결과를 `self.lost_infos: dict[int, dict]` (블록 인덱스 → lost_info)로 보유한다.

### 3. mapping.yaml에 lost_info 기록

`converter/cli.py`에서 `generate_sidecar_mapping()` 호출 시 lost_info를 전달한다.

```python
# converter/cli.py (변경)
sidecar_yaml = generate_sidecar_mapping(
    xhtml_original, markdown_content, page_id,
    lost_infos=converter.lost_infos,  # 추가
)
```

`generate_sidecar_mapping()` (reverse_sync/sidecar.py)에서 각 entry에 lost_info를 병합한다.

```python
# mapping entry 생성 시
entry = {
    'xhtml_xpath': xm.xhtml_xpath,
    'xhtml_type': xm.type,
    'mdx_blocks': matched_indices,
}
if lost_infos and matched_indices:
    # MDX 블록 인덱스로 lost_info 조회
    for mdx_idx in matched_indices:
        if mdx_idx in lost_infos and lost_infos[mdx_idx]:
            entry['lost_info'] = lost_infos[mdx_idx]
            break
entries.append(entry)
```

### 4. roundtrip.json과의 연계

`build_sidecar()` (reverse_sync/sidecar.py)가 roundtrip.json을 빌드할 때, 같은 페이지의 mapping.yaml이 존재하면 `lost_info`를 읽어 `SidecarBlock.lost_info`에 복사한다.

이 연계는 L3 범위에서는 구현하지 않는다. L4에서 `lost_info`를 실제 활용할 때 필요에 따라 구현한다.

### 5. stripped_attrs 범위 제한

`stripped_attrs`는 수가 매우 많고 (style, class, data-*, ac:local-id 등 거의 모든 블록에 존재), L4에서의 활용 가치가 낮다. L3에서는 **emoticons, links, filenames, adf_extensions** 4개 카테고리만 구현한다. `stripped_attrs`는 필요 시 후속 Phase에서 추가한다.

## 인수 기준

1. **기능:** 비가역 정보(emoticon, link, filename, adf_extension)를 포함하는 testcase 블록의 mapping.yaml에 `lost_info`가 기록됨
2. **회귀 없음:** 기존 splice 21/21 byte-equal 유지
3. **테스트:** 기존 테스트 전부 통과 + lost_info 수집 유닛 테스트

## 구현 순서 (개략)

1. `LostInfoCollector` 클래스 작성 + 유닛 테스트
2. `converter/core.py` 수집 지점에 collector 연결 (emoticon → link → filename → adf_extension)
3. `generate_sidecar_mapping()`에 lost_info 전달 경로 추가
4. mapping.yaml 스키마 version 2 반영
5. testcase 검증: 실제 testcase에서 lost_info 기록 확인
6. 기존 테스트 회귀 검증

## 범위 외 (L4 이후)

- `lost_info`를 활용한 역순변환 품질 개선
- `roundtrip.json`의 `SidecarBlock.lost_info` 연계
- `stripped_attrs` 수집
- lost_info의 entry별 분배 (현재는 페이지 전체 수준)

## 구현 노트 (2026-02-17)

설계 대비 실제 구현의 차이점:

1. **LostInfoCollector 위치:** `converter/core.py` 인라인이 아닌 별도 `converter/lost_info.py` 모듈로 분리
2. **collector 단위:** 블록별 collector가 아닌, `ConfluenceToMarkdown` 전체에 하나의 collector를 두고 모든 파서에 전파
3. **lost_info 저장 위치:** entry별 `lost_info` 필드가 아닌, mapping.yaml 최상위 `lost_info` 필드로 기록. entry별 분배는 L4에서 필요 시 구현
4. **stripped_attrs:** 범위 외로 미구현 (설계 문서 §5와 동일)
