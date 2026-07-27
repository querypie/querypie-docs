## Why

현재 Confluence 수집기는 page 전용 child API와 `page.xhtml` 중심 변환 흐름을 사용합니다. 이 때문에 page 아래에 있는 folder를 발견하지 못하고, folder 하위 page가 `var/pages.<code>.yaml`과 MDX 출력에서 함께 누락됩니다.

Confluence folder를 본문 없는 예외로만 취급하면 계층 탐색, navigation, landing page, 이동·이름 변경 후 정리 동작이 서로 달라집니다. Folder를 page와 함께 content tree의 정식 노드로 저장하고 변환하는 계약이 필요합니다.

## What Changes

- `page`와 `folder`를 구분하는 typed content tree를 도입합니다.
- `--remote`가 page와 folder의 `direct-children` API를 끝까지 순회하여 전체 계층을 갱신합니다.
- folder API 응답을 `var/{folder_id}/folder.v2.yaml`과 `children.v2.yaml`에 저장합니다.
- `pages.<code>.yaml`에 각 노드의 `type`과 계층·출력 경로를 기록합니다.
- `convert_all.py`가 folder용 MDX landing page를 생성합니다.
- folder MDX에는 Confluence 순서의 직계 자식 `page`와 `folder`만 표시합니다.
- 생성된 MDX와 navigation의 소유권을 manifest로 기록하고, 이동·이름 변경·삭제로 더 이상 유효하지 않은 생성 파일을 안전하게 제거합니다.
- `--recent`는 저장된 계층을 사용하여 기존 page의 내용만 갱신하고, 계층 변화는 다음 `--remote` 실행에서 반영합니다.

## Capabilities

### New Capabilities

- Confluence folder metadata와 직계 자식 관계의 로컬 snapshot
- 직계 자식 목록을 제공하는 folder MDX landing page
- sync profile별 생성 파일 manifest와 stale output 정리

### Modified Capabilities

- Confluence child traversal을 page-only 순회에서 typed `page`/`folder` 순회로 변경합니다.
- catalog와 navigation 생성을 XHTML 존재 여부와 분리합니다.
- `--remote`, `--recent`, `--local`의 계층 갱신 책임을 명확히 구분합니다.

## Impact

- 주요 구현 surface: `confluence-mdx/bin/fetch/**`, `confluence-mdx/bin/convert_all.py`, `confluence-mdx/bin/converter/cli.py`
- 저장 형식: `confluence-mdx/var/{content_id}/**`, `confluence-mdx/var/pages.<code>.yaml`, sync profile별 conversion manifest
- 출력 형식: `src/content/ko/**`를 가리키는 `confluence-mdx/target/ko/**`의 MDX와 `_meta.ts`
- 테스트 surface: API endpoint/pagination, mixed content tree, 실행 모드, folder MDX, navigation, stale output cleanup
- 호환성: 기존 page 변환과 folder가 sync root인 QCP profile을 유지해야 합니다.
