## Context

현재 fetch pipeline은 다음 결합 때문에 page 아래 folder를 완전하게 처리하지 못합니다.

- `ApiClient.get_child_pages()`가 page-only `/children` endpoint를 사용합니다.
- 재귀 호출이 child의 `id`만 전달하여 `type`을 잃습니다.
- cache가 없는 non-root content는 항상 `page`로 간주합니다.
- `Stage4Processor`가 `page.v1.yaml`의 ancestor와 title을 요구합니다.
- `convert_all.py`는 `page.xhtml`이 있는 항목만 변환합니다.
- `_meta.ts` 생성이 개별 XHTML 변환의 side effect입니다.

Folder는 Confluence 본문을 갖지 않지만, 문서 사이트에서는 이동 가능한 landing page이자 하위 문서의 경로·순서를 결정하는 정식 content node입니다.

## Goals / Non-Goals

### Goals

- page 아래와 folder 아래의 folder를 동일한 규칙으로 발견하고 저장합니다.
- folder와 직계 자식 API 응답을 `var/{folder_id}/`에 보존합니다.
- folder 자체에 MDX landing page를 생성합니다.
- folder MDX에는 직계 자식 `page`와 `folder`만 Confluence 순서대로 표시합니다.
- nested folder는 현재 목록에서 link 하나로만 표현하고, nested folder의 자식은 해당 folder MDX에서 표시합니다.
- folder 이동·이름 변경·삭제 후 이전 생성 파일을 안전하게 정리합니다.
- 기존 page 변환과 QM/QCP sync profile을 회귀시키지 않습니다.

### Non-Goals

- `database`, `whiteboard`, `embed`를 MDX로 변환하거나 navigation에 노출하는 기능
- `--recent`에서 folder 생성·이동·이름 변경을 즉시 감지하는 기능
- folder MDX의 수동 편집 보존
- folder MDX의 reverse sync
- 기존 attachment lifecycle 전체를 재설계하는 작업

## Decisions

### Decision: `page`와 `folder`를 typed content node로 순회합니다

재귀 순회의 입력을 page ID 문자열에서 최소 다음 정보를 가진 child reference로 변경합니다.

```text
ContentRef
  id
  type
  title
  childPosition
```

내부 모델은 `ContentNode`로 일반화하되, 기존 catalog consumer와의 호환성을 위해 serialized identity key는 당분간 `page_id`를 유지하고 `type: page|folder`를 추가합니다.

```yaml
- page_id: "2167636017"
  type: folder
  title: MCP Server
  title_orig: MCP Server
  breadcrumbs:
    - 관리자 매뉴얼
    - MCP Server
  breadcrumbs_en:
    - Administrator Manual
    - MCP Server
  path:
    - administrator-manual
    - mcp-server
```

부모가 `page`이면 `GET /api/v2/pages/{id}/direct-children`, 부모가 `folder`이면 `GET /api/v2/folders/{id}/direct-children`을 사용합니다. 두 endpoint 모두 cursor pagination을 끝까지 따라가고, 결과를 `childPosition`으로 안정 정렬합니다.

`page`와 `folder` 외 child는 재귀 순회와 catalog에서 제외합니다. 경고에는 최소 `parent_id`, `id`, `type`, `title`을 남겨 누락이 의도된 범위 제외임을 확인할 수 있게 합니다.

#### 고려한 대안

1. `descendants` API 한 번으로 tree를 구성하는 방식
   - 전체 발견에는 효율적이지만, folder별 직계 자식 snapshot 저장 요구를 만족하려면 결국 각 folder의 `direct-children` 요청이 추가됩니다.
   - discovery 결과와 저장된 직계 자식 결과 사이의 불일치 처리도 필요하므로 이번 변경에서는 선택하지 않습니다.
2. 현재 page 중심 stage에 folder 조건문만 추가하는 방식
   - `Stage2`, `Stage3`, `Stage4`, converter마다 예외가 반복되고 새로운 content type 추가 시 분기가 확산되므로 선택하지 않습니다.
3. typed `direct-children` 재귀 순회
   - 현재 구조에서 가장 작은 변경으로 API routing, ordering, local replay를 같은 snapshot에 맞출 수 있어 선택합니다.

### Decision: raw 저장 형식은 content type별로 구분합니다

Page는 기존 파일을 유지합니다.

```text
var/{page_id}/
├── page.v1.yaml
├── page.v2.yaml
├── children.v2.yaml
├── attachments.v1.yaml
└── page.xhtml
```

Folder는 다음 파일만 생성합니다.

```text
var/{folder_id}/
├── folder.v2.yaml
└── children.v2.yaml
```

- `folder.v2.yaml`: `GET /api/v2/folders/{id}` metadata 응답
- `children.v2.yaml`: 모든 cursor page의 `results`를 합친 직계 자식 snapshot

Folder에는 `page.v1.yaml`, `page.v2.yaml`, `page.xhtml`, `page.html`, `page.adf`, `attachments.v1.yaml`, attachment binary를 만들지 않습니다. 기존에 잘못 생성된 page 전용 파일이 있더라도 folder 처리의 입력으로 사용하지 않습니다.

Pagination을 합친 `children.v2.yaml`은 기존 consumer가 읽는 `results` shape을 유지합니다. 전체 수집이 실패하면 이전 snapshot을 부분 결과로 덮어쓰지 않고 해당 node의 remote fetch를 실패로 처리합니다.

### Decision: breadcrumb와 path는 tree traversal context에서 계산합니다

Folder는 V1 ancestor 응답이 없으므로 `Stage4Processor`가 `page.v1.yaml`만 읽는 현재 방식으로는 catalog entry를 만들 수 없습니다. 순회 함수가 부모의 `breadcrumbs`를 child에게 전달하고, page/folder metadata의 title을 붙여 현재 tree snapshot 기준 breadcrumb를 계산합니다.

- page title: `page.v1.yaml`의 정제된 title을 우선하고 V2 metadata를 fallback으로 사용합니다.
- folder title: `folder.v2.yaml`의 정제된 title을 사용합니다.
- path: 기존 title translation과 `slugify` 규칙을 page와 folder에 동일하게 적용합니다.
- child display title과 link path: `children.v2.yaml`에 복제된 title/path가 아니라 최신 catalog entry를 사용합니다.
- child order: 부모의 `children.v2.yaml`에 저장된 `childPosition`을 사용합니다.

이 분리는 `--recent`가 기존 page title/body를 갱신했을 때 folder의 cached child snapshot을 다시 받지 않아도 landing page의 label과 link가 최신 catalog를 사용하게 합니다.

### Decision: 계층 구조는 `--remote`에서만 갱신합니다

실행 모드별 책임은 다음과 같습니다.

| Mode | API 호출 | 계층 snapshot | catalog |
| --- | --- | --- | --- |
| `--remote` | page/folder metadata와 `direct-children`, 필요 시 page body/attachment | 전체 갱신 | 새 snapshot으로 재구성 |
| `--recent` | CQL로 발견한 기존 page의 metadata/body/attachment | 갱신하지 않음 | 저장된 `children.v2.yaml`을 따라 재구성 |
| `--local` | 없음 | 갱신하지 않음 | 저장된 metadata와 `children.v2.yaml`만으로 재구성 |

`--recent`의 page fetch는 `children.v2.yaml`을 덮어쓰지 않습니다. 부분적으로만 새 계층이 섞이면 metadata가 없는 folder를 발견하거나 일부 이동만 반영하는 불완전한 catalog가 만들어질 수 있기 때문입니다.

운영자는 folder 생성·이동·이름 변경·삭제를 반영해야 할 때 `--remote`를 실행합니다. 이 eventual consistency는 승인된 동작입니다.

### Decision: folder MDX는 별도 deterministic generator가 만듭니다

`convert_all.py`는 catalog node의 `type`에 따라 변환기를 선택합니다.

- `page`: 기존 XHTML converter를 실행합니다.
- `folder`: folder MDX generator를 실행합니다.

Folder generator는 XHTML converter나 `mapping.yaml` 생성기를 호출하지 않습니다. Folder MDX는 변환기가 전부 소유하며 매 실행마다 완전히 덮어씁니다.

예상 출력은 다음과 같습니다.

```mdx
---
title: 'MCP Server'
confluenceUrl: 'https://querypie.atlassian.net/wiki/spaces/QM/folder/2167636017'
---

# MCP Server

## 하위 문서

- [MAC General Configurations](./mcp-server/mac-general-configurations)
- [MCP Server Connection Management](./mcp-server/mcp-server-connection-management)
- [MCP Access Control](./mcp-server/mcp-access-control)
```

Link는 현재 folder MDX 파일에서 child MDX 파일까지의 상대 filesystem path를 계산한 뒤 `.mdx` suffix를 제거하고 POSIX separator로 기록합니다. 이를 통해 깊이가 다른 folder와 nested folder도 같은 알고리즘을 사용합니다.

Nested folder가 직계 자식이면 해당 folder landing page link만 한 줄로 표시합니다. Nested folder의 child는 현재 MDX에 펼치지 않습니다.

지원되는 직계 자식이 없는 folder도 MDX를 생성합니다.

```mdx
## 하위 문서

하위 문서가 없습니다.
```

`confluenceUrl`은 `folder.v2.yaml`의 `_links.base`, sync profile의 `space_key`, folder ID를 사용해 `{base}/spaces/{space_key}/folder/{id}` 형식으로 생성합니다. API가 `_links.webui`를 제공하면 해당 값을 우선 사용할 수 있지만, `GET /folders/{id}`의 응답 계약은 `_links.webui`를 보장하지 않으므로 필수 입력으로 간주하지 않습니다. `_links.base`가 없으면 `convert_all.py --base-url` 값을 사용합니다.

### Decision: navigation 생성은 content conversion과 분리합니다

현재 `converter/cli.py`의 `generate_meta_from_children()` side effect를 제거하고, `convert_all.py`의 catalog-level navigation pass로 이동합니다.

Navigation pass는 각 parent node의 `children.v2.yaml`과 catalog를 사용하여 다음을 생성합니다.

```text
administrator-manual/_meta.ts
  mcp-server: MCP Server

administrator-manual/mcp-server/_meta.ts
  mac-general-configurations: MAC General Configurations
  mcp-server-connection-management: MCP Server Connection Management
  mcp-access-control: MCP Access Control
```

목록과 마찬가지로 지원되는 직계 자식만 포함하고 `childPosition` 순서를 유지합니다. Child의 MDX가 현재 conversion plan에 없거나 생성에 실패한 경우 해당 navigation entry를 만들지 않고 전체 conversion을 실패로 보고합니다.

### Decision: sync profile별 manifest로 stale output을 정리합니다

`convert_all.py`는 sync profile별 manifest에 자신이 생성한 MDX와 `_meta.ts`를 기록합니다. Manifest는 `var/convert-manifest.<sync-code>.yaml`에 저장하며 최소 `page_id`, `type`, output 상대 경로를 보존합니다.

정리 순서는 다음과 같습니다.

1. 이전 manifest를 읽습니다.
2. 현재 catalog의 page/folder MDX와 navigation을 모두 생성하고 검증합니다.
3. 하나라도 실패하면 이전 파일 삭제와 manifest 교체를 수행하지 않습니다.
4. 모두 성공하면 `previous_paths - current_paths`만 삭제합니다.
5. 빈 directory만 아래에서 위로 제거하고, manifest 밖의 파일이나 비어 있지 않은 directory는 보존합니다.
6. 현재 manifest를 atomic replace합니다.

모든 삭제 대상은 resolve 후 configured output root 내부인지 검사합니다. Manifest가 가리키더라도 output root 밖의 경로, 허용하지 않은 suffix, 예상하지 않은 `_meta.ts` 위치는 삭제하지 않고 오류로 처리합니다.

Folder 이동·이름 변경 시 folder landing MDX뿐 아니라 경로가 바뀐 descendant page/folder MDX와 generated `_meta.ts`도 같은 방식으로 정리됩니다. Attachment cleanup은 이번 변경 범위에 포함하지 않습니다.

### Decision: root node는 catalog에 남기되 기존 출력 정책을 유지합니다

QM의 page root와 QCP의 folder root 모두 typed node로 수집합니다. Root는 breadcrumb/path 계산의 기준이며 catalog에 포함하지만, 기존과 같이 sync root 자체의 MDX는 생성하지 않습니다. Root의 직계 자식 navigation 생성 여부는 현재 site root 정책을 유지하고 회귀 테스트로 고정합니다.

## Risks / Trade-offs

- `--remote`는 각 parent의 `direct-children`을 호출하므로 전체 동기화 시간이 유지되거나 늘어날 수 있습니다. 정확한 raw snapshot과 단순한 local replay를 우선합니다.
- `--recent` 직후에는 Confluence 계층과 로컬 출력이 일시적으로 다를 수 있습니다. 이는 승인된 eventual consistency이며 로그와 README에 명시합니다.
- 중앙 navigation pass로 이동하면 기존 converter 단독 실행에서 `_meta.ts`가 생성되지 않습니다. 단일 XHTML 변환과 전체 site navigation 생성의 책임을 분리하고, README와 테스트 명령을 갱신해야 합니다.
- manifest 도입 전 생성된 stale 파일은 소유권을 증명할 수 없어 최초 실행에서 자동 삭제하지 않습니다. 첫 성공 실행이 baseline manifest를 만든 뒤부터 안전한 정리가 가능합니다.
- folder MDX는 reverse sync 대상이 아닙니다. Folder에 `mapping.yaml`이 없고 Confluence body가 없다는 점을 명확한 진단으로 표시해야 합니다.

## Migration Plan

1. typed model과 API client pagination을 추가합니다.
2. `--remote`로 전체 QM/QCP tree를 다시 받아 folder raw snapshot과 typed catalog를 생성합니다.
3. folder generator와 중앙 navigation pass를 추가합니다.
4. 최초 `convert_all.py` 성공 시 manifest baseline을 기록합니다. 이 실행에서는 기존 manifest가 없으므로 stale output을 삭제하지 않습니다.
5. 두 번째 fixture run에서 folder 이동·이름 변경·삭제를 재현하여 stale output 정리를 검증합니다.
6. README에 mode별 hierarchy freshness와 folder 저장/출력 형식을 기록합니다.
7. 구현과 검증이 완료되면 change-local spec을 accepted `contract-confluence-mdx-conversion` spec으로 승격합니다.

## Open Questions

승인된 요구사항 기준으로 구현을 막는 미해결 질문은 없습니다.
