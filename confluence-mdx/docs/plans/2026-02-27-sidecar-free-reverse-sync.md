# Sidecar-Free Reverse Sync 분석

> 작성일: 2026-02-27
> 목적: reverse-sync에서 sidecar(mapping.yaml)를 사용하지 않고, 저장된 API 응답 데이터로 대체하는 방안 검토

---

## 1. 현황: Sidecar 기반 Reverse Sync

### 1.1 현재 데이터 흐름

```
[Forward Conversion]
page.xhtml ──→ converter ──→ expected.mdx
                  └──→ mapping.yaml (sidecar)
                  └──→ lost_info (emoticons, links, images...)

[Reverse Sync]
original.mdx + improved.mdx + page.xhtml + mapping.yaml
    ↓
1. parse_mdx_blocks(original) → MdxBlock[]
2. parse_mdx_blocks(improved) → MdxBlock[]
3. diff_blocks(original, improved) → BlockChange[]
4. record_mapping(page.xhtml) → BlockMapping[]
5. mapping.yaml → mdx_to_sidecar index (MDX idx → xhtml_xpath)
6. patch_builder: 변경 매핑 + XHTML 패치 생성
7. xhtml_patcher: 패치 적용 → patched.xhtml
8. verify: patched.xhtml → verify.mdx → improved.mdx 비교
```

### 1.2 Sidecar가 제공하는 정보

| 정보 | 저장 위치 | 역할 |
|------|-----------|------|
| MDX 블록 인덱스 → XHTML xpath | `mapping.yaml` | O(1) 블록 매핑 조회 |
| XHTML 블록 타입 | `mapping.yaml` | 전략 결정 보조 |
| lost_info (emoticons, links, images...) | `mapping.yaml` | Confluence 전용 요소 복원 |
| xhtml_fragment (byte-exact) | `roundtrip.json` | splice 재조립 |
| separators / envelope | `roundtrip.json` | byte-exact 재조립 |

### 1.3 Sidecar의 문제점

1. **생성 시점 의존**: forward conversion 시 생성되므로, MDX가 편집되면 매핑이 구형화
2. **추가 빌드 스텝**: 매 forward conversion마다 sidecar 생성이 필요
3. **텍스트 매칭 취약성**: `generate_sidecar_mapping()`의 LOOKAHEAD=5 기반 텍스트 매칭이 CJK, 빈 블록, 반복 패턴에서 부정확
4. **유지보수 부담**: sidecar 스키마/생성/소비 코드가 분산 (`sidecar.py` 500+ lines)

---

## 2. 사용 가능한 저장 데이터

### 2.1 데이터 소스 목록

| 파일 | 출처 | 내용 | 현재 사용 |
|------|------|------|-----------|
| `page.xhtml` | Confluence V1 API `body.storage` | Confluence Storage Format XHTML (ground truth) | ✅ reverse-sync 입력 |
| `page.adf` | Confluence V2 API `atlas_doc_format` | Atlassian Document Format JSON | ❌ 미사용 |
| `page.v1.yaml` | Confluence V1 API 전체 응답 | 메타데이터 + body.storage + body.view | ❌ 메타데이터만 |
| `page.v2.yaml` | Confluence V2 API 전체 응답 | 메타데이터 + ADF | ❌ 메타데이터만 |
| `attachments.v1.yaml` | Confluence V1 API | 첨부파일 메타데이터 | ❌ 미사용 |

### 2.2 page.xhtml (이미 사용 중)

Confluence Storage Format XHTML. reverse-sync의 주요 입력이며 ground truth.

현재 `record_mapping(page.xhtml)`으로 블록 구조를 추출하지만, MDX↔XHTML 매핑에는 sidecar를 사용.

### 2.3 page.adf (미사용)

Confluence V2 API에서 반환하는 JSON 문서 모델. 구조적 정보가 풍부:

```json
{
  "type": "doc",
  "content": [
    {
      "type": "heading",
      "attrs": {"level": 2},
      "content": [{"type": "text", "text": "제목"}]
    },
    {
      "type": "paragraph",
      "content": [
        {"type": "text", "text": "일반 텍스트"},
        {"type": "text", "text": "굵은 텍스트", "marks": [{"type": "strong"}]}
      ]
    },
    {
      "type": "table",
      "attrs": {"localId": "uuid-1234"},
      "content": [
        {"type": "tableRow", "content": [
          {"type": "tableHeader", "content": [...]},
          {"type": "tableCell", "content": [...]}
        ]}
      ]
    }
  ]
}
```

**ADF의 장점**:
- JSON 구조 → 파싱이 XHTML보다 단순/안정적
- 노드 타입이 명시적 (`paragraph`, `heading`, `table`, `panel` 등)
- 인라인 마크 분리 (`strong`, `em`, `code` → `marks` 배열)
- 링크 대상이 명시적 (`href`, `collection`, `id` 속성)
- 리스트 중첩이 구조적 (`bulletList` > `listItem` > `bulletList`)

**ADF의 한계**:
- XHTML이 ground truth: Confluence API 업데이트는 XHTML(body.storage) 형식만 수용
- ADF → XHTML 변환이 추가로 필요 (현재 코드 없음)
- ADF와 XHTML의 블록 단위가 다를 수 있음 (1:1 매핑 보장 안됨)
- ADF에 `<ac:*>` Confluence 전용 태그 정보가 일부 누락될 수 있음

---

## 3. 대안 접근법

### 3.1 접근법 A: page.xhtml 런타임 매핑 (sidecar 제거)

**핵심 아이디어**: `generate_sidecar_mapping()`의 텍스트 매칭을 reverse-sync 시점에 수행

```
[Forward Conversion]
page.xhtml ──→ converter ──→ expected.mdx  (sidecar 생성 생략)

[Reverse Sync]
original.mdx + improved.mdx + page.xhtml
    ↓
1. record_mapping(page.xhtml) → BlockMapping[]
2. parse_mdx_blocks(original.mdx) → MdxBlock[]
3. 런타임 텍스트 매칭: MDX blocks ↔ XHTML blocks (현재 sidecar 생성 로직 재사용)
4. diff_blocks + patch_builder + xhtml_patcher (기존과 동일)
```

**변경 범위**:
- `reverse_sync_cli.py`: mapping.yaml 로드 대신 런타임 매핑 생성
- `patch_builder.py`: `find_mapping_by_sidecar()` → 런타임 인덱스 조회로 교체
- lost_info: page.xhtml에서 런타임 추출 (아래 3.4 참조)

**장점**:
- sidecar 생성 스텝 완전 제거
- 항상 현재 page.xhtml 기준으로 매핑 → 구형화 문제 없음
- 기존 텍스트 매칭 로직 재사용 가능 (`generate_sidecar_mapping` 내부)

**단점**:
- reverse-sync 실행 시간 증가 (매핑 생성이 런타임으로 이동)
- original.mdx가 편집된 경우 텍스트 매칭 정확도가 sidecar보다 낮을 수 있음
  - sidecar는 converter 출력 MDX 기준으로 생성 (page.xhtml과 정확히 대응)
  - 런타임은 편집된 original.mdx 기준 (page.xhtml과 부분적 불일치 가능)

**정확도 분석**:

현재 sidecar 매핑도 결국 텍스트 매칭이다. `generate_sidecar_mapping()`은 4단계 폴백:
1. 완전 일치
2. 공백 축약 일치
3. 50자 prefix 매치
4. 20자 prefix 매치

동일한 알고리즘을 reverse-sync 시점에 실행하면 동일한 정확도를 얻는다. 단, 입력 MDX가 converter 출력과 다를 경우 (편집됨) 정확도가 떨어진다.

**대응 방안**: `expected.mdx` (converter 출력, 편집 전)를 매핑 생성에 사용하고, `original.mdx` (편집 후)는 diff에만 사용. 이렇게 하면 sidecar와 동일한 정확도를 얻으면서 mapping.yaml 파일이 불필요.

### 3.2 접근법 B: ADF 기반 구조적 매핑

**핵심 아이디어**: page.adf의 JSON 구조를 활용하여 블록 정렬

```
[Reverse Sync]
original.mdx + improved.mdx + page.xhtml + page.adf
    ↓
1. JSON.parse(page.adf) → ADF 노드 트리
2. parse_mdx_blocks(original.mdx) → MdxBlock[]
3. ADF 노드 ↔ MDX 블록 구조적 매칭 (타입 + 텍스트)
4. ADF 노드 ↔ XHTML 블록 매핑 (ADF localId → XHTML ac:local-id)
5. 간접 매핑: MDX → ADF → XHTML
```

**장점**:
- 구조적 정보 활용 가능 (블록 타입, 중첩 수준, 링크 대상)
- 텍스트만으로 매칭할 때의 모호성 감소
- ADF의 명시적 링크 정보로 `<ac:link>` 복원 가능성

**단점**:
- ADF 파서 신규 구현 필요 (현재 코드 없음)
- ADF → XHTML 매핑이 비자명적 (Confluence 내부 변환 규칙 역공학 필요)
- ADF 노드와 XHTML 블록의 1:1 대응 보장 안됨
- 최종 출력은 여전히 XHTML (ADF로 Confluence 업데이트 불가)
- 새로운 추상 레이어 추가로 복잡도 증가

### 3.3 접근법 C: 하이브리드 (page.xhtml 런타임 매핑 + ADF 보조)

**핵심 아이디어**: 접근법 A를 기본으로 하되, ADF 정보를 보조적으로 활용

```
[Reverse Sync]
1. 접근법 A 방식으로 page.xhtml 런타임 매핑 수행
2. 텍스트 매칭 실패 시 ADF 노드 타입/텍스트로 보조 매칭
3. ADF의 링크/이미지 메타데이터로 lost_info 보충
```

**장점**:
- 기본 경로는 검증된 텍스트 매칭 활용
- ADF는 폴백/보충 역할만 → 의존도 낮음
- 점진적 도입 가능

**단점**:
- 두 가지 데이터 소스 관리 필요
- ADF 파서 구현 여전히 필요 (보조적이더라도)
- 복잡도 대비 실제 개선 효과 불확실

### 3.4 Lost Info 런타임 추출

sidecar 없이 lost_info를 얻는 방법:

**page.xhtml에서 직접 추출 (접근법 A, C 공통)**:

```python
def extract_lost_info_from_xhtml(xhtml: str) -> dict:
    """page.xhtml에서 Confluence 전용 요소를 스캔하여 lost_info를 생성."""
    soup = BeautifulSoup(xhtml, 'html.parser')
    lost = {}

    # emoticons: <ac:emoticon> → fallback + raw
    emoticons = soup.find_all('ac:emoticon')
    if emoticons:
        lost['emoticons'] = [
            {'raw': str(e), 'fallback': e.get('ac:emoji-fallback', '')}
            for e in emoticons
        ]

    # links: <ac:link> → content_title + raw
    links = soup.find_all('ac:link')
    if links:
        lost['links'] = [
            {'raw': str(l), 'content_title': _extract_title(l)}
            for l in links
        ]

    # images: <ac:image> → src + raw
    images = soup.find_all('ac:image')
    if images:
        lost['images'] = [
            {'raw': str(img), 'src': _extract_src(img)}
            for img in images
        ]

    return lost
```

이 방식은 forward converter의 `LostInfoCollector`와 동일한 정보를 page.xhtml에서 직접 추출한다. forward conversion 결과에 의존하지 않으므로, sidecar 없이도 lost_info를 복원할 수 있다.

**ADF에서 추출 (접근법 B, C)**:

ADF에는 링크 대상, 이미지 참조, 미디어 컬렉션 ID 등이 명시적으로 포함되어 있어 XHTML 파싱보다 신뢰도 높은 메타데이터를 얻을 수 있다. 단, emoticon의 `<ac:emoticon>` raw 태그는 ADF에 없으므로 XHTML이 여전히 필요.

---

## 4. 비교 분석

### 4.1 접근법별 비교

| 항목 | 현재 (sidecar) | A: XHTML 런타임 | B: ADF 기반 | C: 하이브리드 |
|------|---------------|-----------------|-------------|--------------|
| **매핑 정확도** | 높음 (converter 출력 기준) | 동등 (expected.mdx 사용 시) | 높음 (구조적 매칭) | 동등~높음 |
| **구현 난이도** | 기존 | 낮음 (리팩토링) | 높음 (ADF 파서 신규) | 중간 |
| **런타임 비용** | 낮음 (pre-computed) | 약간 증가 | 상당 증가 | 약간 증가 |
| **유지보수 부담** | 높음 (sidecar 스키마) | 낮음 (파일 제거) | 높음 (ADF + XHTML) | 중간 |
| **구형화 위험** | 있음 | 없음 | 없음 | 없음 |
| **코드 변경 범위** | - | 중간 | 대형 | 대형 |
| **추가 데이터 의존** | mapping.yaml | 없음 | page.adf | page.adf |

### 4.2 구현 비용 대비 가치

**접근법 A**가 최적의 비용/가치 비율을 가진다:

- sidecar 생성 스텝 제거 → 파이프라인 단순화
- 기존 코드 재사용 가능 (generate_sidecar_mapping 로직)
- lost_info는 page.xhtml에서 런타임 추출
- mapping.yaml 파일 불필요 → 저장/관리 제거

**접근법 B, C는 현 시점에서 가치가 낮다**:
- ADF 파서 신규 구현이 대규모 작업
- ADF → XHTML 매핑 규칙의 역공학 필요
- 현재 텍스트 매칭으로 충분한 정확도 달성 중 (16/16 pass)
- ADF 고유 정보(링크 메타데이터 등)는 page.xhtml에서도 추출 가능

---

## 5. 권장안: 접근법 A (page.xhtml 런타임 매핑)

### 5.1 핵심 변경

1. **mapping.yaml 생성 제거**: forward conversion 시 sidecar 생성 스킵
2. **런타임 매핑 생성**: reverse-sync 시점에 `page.xhtml` + `expected.mdx`로 매핑 생성
3. **lost_info 런타임 추출**: page.xhtml에서 Confluence 전용 요소 직접 스캔
4. **mapping.yaml 파일 참조 제거**: 모든 코드에서 mapping.yaml 로드 경로 제거

### 5.2 expected.mdx 활용 전략

매핑 정확도를 sidecar와 동등하게 유지하기 위해, `expected.mdx` (converter 출력, 편집 전 MDX)를 매핑 생성에 사용:

```
런타임 매핑 = generate_sidecar_mapping(page.xhtml, expected.mdx)
```

`expected.mdx`는 forward conversion의 출력이므로 `page.xhtml`과 정확히 대응한다. `original.mdx` (편집된 MDX)가 아닌 `expected.mdx`를 사용함으로써, sidecar와 동일한 매핑 정확도를 보장한다.

**`expected.mdx`의 위치**: forward conversion 시 `var/<page_id>/`에 생성되어 이미 저장되어 있음. mapping.yaml 대신 이 파일을 활용.

### 5.3 데이터 의존성 변경

```
[Before]
reverse-sync 입력: original.mdx, improved.mdx, page.xhtml, mapping.yaml

[After]
reverse-sync 입력: original.mdx, improved.mdx, page.xhtml, expected.mdx
```

`mapping.yaml`이 `expected.mdx`로 대체된다. 두 파일 모두 forward conversion 시 생성되는 파생물이지만, `expected.mdx`는 사람이 읽을 수 있고 다른 용도로도 사용되므로 별도 관리 부담이 없다.

### 5.4 구현 단계

| 단계 | 작업 | 예상 범위 |
|------|------|-----------|
| S1 | `reverse_sync_cli.py`에서 런타임 매핑 생성 경로 추가 (기존 경로와 병존) | 소형 |
| S2 | lost_info 런타임 추출 함수 구현 (`extract_lost_info_from_xhtml`) | 소형 |
| S3 | 전체 테스트케이스 런타임 매핑으로 검증 (16/16 pass 유지 확인) | 검증 |
| S4 | mapping.yaml 생성 코드 제거 / 로드 경로 정리 | 중형 |
| S5 | roundtrip.json (splice rehydrator) 경로 영향 분석 및 정리 | 분석 |

### 5.5 리스크

| 리스크 | 심각도 | 대응 |
|--------|--------|------|
| 런타임 매핑 정확도 저하 | 중 | expected.mdx 사용으로 완화, 테스트케이스로 검증 |
| 런타임 성능 저하 | 낮 | 매핑 생성은 수십ms 수준, 실무 영향 미미 |
| splice rehydrator 영향 | 중 | S5에서 별도 분석 — roundtrip.json은 mapping.yaml과 별개 경로 |
| expected.mdx 부재 시 | 낮 | 폴백: original.mdx로 매핑 생성 (정확도 다소 저하) |

---

## 6. 후속 검토 사항

### 6.1 ADF 활용 (장기)

접근법 A 적용 후, ADF 활용 가치를 재평가:

- **링크 복원**: ADF의 `inlineCard` 노드에 Confluence 페이지 참조 정보가 명시적으로 포함. `<ac:link>` 복원에 활용 가능.
- **테이블 구조**: ADF의 `table` 노드에 `localId`, `layout` 정보가 명시적. XHTML의 `ac:local-id`와 매핑 가능.
- **패널/콜아웃**: ADF의 `panel` 노드 `panelType`이 XHTML의 `ac:structured-macro ac:name`과 대응.

ADF는 XHTML 파싱의 **보조 정보원**으로 점진적 도입이 가능하다.

### 6.2 Rehydrator (splice 경로) 영향

`rehydrator.py`의 splice 경로는 `roundtrip.json`의 `xhtml_fragment` + `mdx_content_hash`에 의존한다. 이것은 mapping.yaml과 별개 경로이므로, 접근법 A의 변경 범위에 포함되지 않는다. 단, 장기적으로 roundtrip.json도 런타임 생성으로 전환할 수 있는지 별도 분석이 필요하다.

---

## 7. 결론

sidecar(mapping.yaml)를 제거하고 `page.xhtml` + `expected.mdx`에서 런타임 매핑을 생성하는 **접근법 A**가 최적이다.

- 기존 텍스트 매칭 알고리즘을 재사용하여 동일한 정확도를 유지
- forward conversion 파이프라인에서 sidecar 생성 스텝 제거
- lost_info는 page.xhtml에서 런타임 추출하여 동일한 복원 능력 유지
- ADF 활용은 장기 과제로 별도 검토

현재 16/16 테스트 pass 상태에서, 런타임 매핑으로 전환 후에도 동일한 결과를 유지하는 것이 검증 기준이다.
