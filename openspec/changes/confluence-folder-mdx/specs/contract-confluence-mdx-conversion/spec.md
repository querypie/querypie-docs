# contract-confluence-mdx-conversion

## Purpose

Confluence의 `page`와 `folder` 계층을 손실 없이 저장하고, QueryPie 문서 사이트의 MDX와 navigation으로 결정적으로 변환하는 계약을 정의합니다.

## References

- GitHub issue #1028
- Atlassian REST API v2 `Children`, `Folder`
- `confluence-mdx/bin/fetch_cli.py`
- `confluence-mdx/bin/convert_all.py`

## ADDED Requirements

### Requirement: Typed content tree

Confluence fetcher는 지원되는 모든 content node를 `page` 또는 `folder` type과 함께 보존하고 순회해야 합니다(SHALL).

#### Scenario: page 아래 folder 발견

- GIVEN page의 `direct-children` 응답에 `type: folder`인 child가 있습니다.
- WHEN `fetch_cli.py --remote`를 실행합니다.
- THEN fetcher는 child ID와 `folder` type을 다음 재귀 호출까지 보존해야 합니다(SHALL).
- AND folder endpoint로 metadata와 직계 자식을 요청해야 합니다(SHALL).

#### Scenario: 지원하지 않는 child type

- GIVEN 직계 자식에 `database`, `whiteboard`, `embed` 중 하나가 있습니다.
- WHEN content tree를 순회합니다.
- THEN 해당 child를 catalog, MDX, navigation에서 제외해야 합니다(SHALL).
- AND parent ID, child ID, type, title을 식별할 수 있는 경고를 기록해야 합니다(SHALL).

#### Scenario: current가 아닌 child status

- GIVEN `direct-children` 응답에 `status`가 `current`가 아닌 page 또는 folder child가 있습니다.
- WHEN content tree를 순회합니다.
- THEN 해당 child를 catalog, MDX, navigation에서 제외해야 합니다(SHALL).
- AND parent ID, child ID, type, status, title을 식별할 수 있는 경고를 기록해야 합니다(SHALL).
- AND 해당 child의 page 또는 folder metadata endpoint를 호출하지 않아야 합니다(SHALL NOT).

### Requirement: Direct children API and pagination

Fetcher는 parent type에 맞는 V2 `direct-children` endpoint를 사용하고 모든 cursor page를 수집해야 합니다(SHALL).

#### Scenario: page의 직계 자식

- GIVEN parent type이 `page`입니다.
- WHEN 직계 자식을 원격 수집합니다.
- THEN `/api/v2/pages/{id}/direct-children`을 호출해야 합니다(SHALL).

#### Scenario: folder의 직계 자식

- GIVEN parent type이 `folder`입니다.
- WHEN 직계 자식을 원격 수집합니다.
- THEN `/api/v2/folders/{id}/direct-children`을 호출해야 합니다(SHALL).

#### Scenario: cursor가 있는 응답

- GIVEN `direct-children` 응답에 다음 cursor가 있습니다.
- WHEN 직계 자식 snapshot을 저장합니다.
- THEN 다음 cursor가 없어질 때까지 요청해야 합니다(SHALL).
- AND 모든 `results`를 빠짐없이 `children.v2.yaml`에 저장해야 합니다(SHALL).
- AND 중간 요청이 실패하면 부분 snapshot으로 이전 파일을 덮어쓰지 않아야 합니다(SHALL NOT).

### Requirement: Folder raw storage

Fetcher는 folder API 결과를 해당 content ID 디렉터리에 type별 파일로 저장해야 합니다(SHALL).

#### Scenario: folder 저장

- GIVEN folder ID가 `2167636017`입니다.
- WHEN folder를 원격 수집합니다.
- THEN metadata를 `var/2167636017/folder.v2.yaml`에 저장해야 합니다(SHALL).
- AND pagination을 합친 직계 자식을 `var/2167636017/children.v2.yaml`에 저장해야 합니다(SHALL).
- AND folder용 `page.v1.yaml`, `page.v2.yaml`, `page.xhtml`, attachment artifact를 새로 만들지 않아야 합니다(SHALL NOT).

### Requirement: Typed catalog and paths

`pages.<code>.yaml`은 각 지원 node의 `page_id`, `type`, title, breadcrumb, path를 기록해야 합니다(SHALL).

#### Scenario: folder가 포함된 path

- GIVEN `관리자 매뉴얼` page 아래 `MCP Server` folder와 그 아래 page가 있습니다.
- WHEN catalog를 생성합니다.
- THEN folder entry에 `type: folder`가 있어야 합니다(SHALL).
- AND 하위 page의 path에 folder의 `mcp-server` segment가 있어야 합니다(SHALL).

#### Scenario: local replay

- GIVEN page/folder metadata와 `children.v2.yaml`이 `var/`에 저장되어 있습니다.
- WHEN `fetch_cli.py --local`을 실행합니다.
- THEN API 호출 없이 같은 typed catalog와 ordering을 재구성해야 합니다(SHALL).

### Requirement: Hierarchy freshness by mode

Fetcher는 hierarchy snapshot을 `--remote`에서 갱신하고 `--recent`와 `--local`에서는 저장된 snapshot을 사용해야 합니다(SHALL).

#### Scenario: remote hierarchy refresh

- GIVEN Confluence에서 folder가 생성, 이동, 이름 변경 또는 삭제되었습니다.
- WHEN `fetch_cli.py --remote`를 실행합니다.
- THEN 전체 지원 tree와 catalog가 현재 hierarchy를 반영해야 합니다(SHALL).

#### Scenario: recent content refresh

- GIVEN 마지막 `--remote` 이후 hierarchy가 변경되었습니다.
- WHEN `fetch_cli.py --recent`를 실행합니다.
- THEN 기존 page metadata/body/attachment를 갱신할 수 있습니다(MAY).
- AND 저장된 `children.v2.yaml` hierarchy를 갱신하지 않아야 합니다(SHALL NOT).
- AND hierarchy 변경은 다음 `--remote` 전까지 반영되지 않을 수 있습니다(MAY).

### Requirement: Folder MDX landing page

Converter는 root가 아닌 모든 catalog `folder`에 deterministic MDX landing page를 생성해야 합니다(SHALL).

#### Scenario: 직계 자식 목록

- GIVEN folder에 직계 자식 `page`와 `folder`가 있습니다.
- WHEN `convert_all.py`를 실행합니다.
- THEN folder MDX에 `title`과 `confluenceUrl` frontmatter를 기록해야 합니다(SHALL).
- AND `confluenceUrl`은 API `_links.base`, sync profile의 `space_key`, folder ID로 생성해야 합니다(SHALL).
- AND 동일한 title의 H1과 `## 하위 문서` heading을 기록해야 합니다(SHALL).
- AND 지원되는 직계 자식을 `childPosition` 순서의 link 목록으로 기록해야 합니다(SHALL).
- AND link label과 target path는 catalog에서 해석해야 합니다(SHALL).

#### Scenario: folder metadata에 web UI link가 없음

- GIVEN `folder.v2.yaml`의 `_links`에 `base`만 있고 `webui`가 없습니다.
- WHEN folder MDX를 생성합니다.
- THEN `{base}/spaces/{space_key}/folder/{id}` 형식의 `confluenceUrl`을 생성해야 합니다(SHALL).

#### Scenario: nested folder

- GIVEN folder의 직계 자식이 다른 folder이고 그 아래 descendant page가 있습니다.
- WHEN 부모 folder MDX를 생성합니다.
- THEN nested folder landing page link를 직계 자식 한 항목으로 표시해야 합니다(SHALL).
- AND descendant page를 부모 folder 목록에 펼치지 않아야 합니다(SHALL NOT).
- AND descendant page는 nested folder MDX의 직계 자식 목록에 표시해야 합니다(SHALL).

#### Scenario: 빈 folder

- GIVEN 지원되는 직계 자식이 없는 folder입니다.
- WHEN folder MDX를 생성합니다.
- THEN MDX 파일을 생성해야 합니다(SHALL).
- AND `## 하위 문서` 아래에 `하위 문서가 없습니다.`를 표시해야 합니다(SHALL).

#### Scenario: 재변환

- GIVEN 기존 folder MDX에 수동 편집이 있습니다.
- WHEN `convert_all.py`를 다시 실행합니다.
- THEN frontmatter, 제목, 직계 자식 목록을 전부 재생성하여 기존 내용을 덮어써야 합니다(SHALL).

### Requirement: Navigation generation

Converter는 page XHTML 변환 여부와 독립적으로 typed catalog와 직계 자식 snapshot에서 navigation을 생성해야 합니다(SHALL).

#### Scenario: folder navigation

- GIVEN parent page 아래 folder와 folder 아래 page가 있습니다.
- WHEN 전체 변환이 성공합니다.
- THEN parent `_meta.ts`에 folder를 기록해야 합니다(SHALL).
- AND folder directory의 `_meta.ts`에 직계 자식 page/folder를 `childPosition` 순서로 기록해야 합니다(SHALL).

### Requirement: Generated output lifecycle

Converter는 sync profile별 manifest로 자신이 만든 MDX와 navigation을 추적하고 stale output만 안전하게 제거해야 합니다(SHALL).

#### Scenario: folder 이동 또는 이름 변경

- GIVEN 이전 성공 변환의 manifest가 있습니다.
- AND `--remote` 결과에서 folder 또는 descendant의 output path가 달라졌습니다.
- WHEN 새 catalog의 전체 변환이 성공합니다.
- THEN 새 경로에 output을 생성해야 합니다(SHALL).
- AND 이전 manifest에는 있지만 현재 manifest에는 없는 생성 파일을 삭제해야 합니다(SHALL).
- AND manifest에 없는 파일을 삭제하지 않아야 합니다(SHALL NOT).

#### Scenario: conversion failure

- GIVEN 이전 성공 변환의 manifest가 있습니다.
- WHEN 현재 전체 변환 중 하나 이상의 output 생성이 실패합니다.
- THEN 이전 output을 stale file로 삭제하지 않아야 합니다(SHALL NOT).
- AND 이전 manifest를 교체하지 않아야 합니다(SHALL NOT).

#### Scenario: ephemeral container 재실행

- GIVEN `docker compose run --rm`으로 변환을 실행합니다.
- WHEN 성공한 변환이 profile manifest를 갱신하고 container가 종료됩니다.
- THEN manifest 변경은 host의 추적 가능한 경로에 남아야 합니다(SHALL).
- AND 다음 container 실행은 이전 성공 변환의 manifest를 읽어야 합니다(SHALL).
- AND manifest directory를 mount하여 atomic file 교체를 지원해야 합니다(SHALL).
- AND atomic replace 대상 manifest file 자체를 개별 mount point로 사용하지 않아야 합니다(SHALL NOT).

#### Scenario: 공유 output root의 profile 소유권 이전

- GIVEN 두 sync profile이 같은 output root를 사용합니다.
- AND 현재 profile에서 stale인 경로를 다른 profile의 manifest가 소유합니다.
- WHEN 현재 profile의 stale cleanup을 실행합니다.
- THEN 다른 profile이 소유한 output을 삭제하지 않아야 합니다(SHALL NOT).
- AND 현재 profile manifest에서는 해당 stale 경로의 소유권을 제거해야 합니다(SHALL).

#### Scenario: 공유 output root의 current path 충돌

- GIVEN 두 sync profile이 같은 output root를 사용합니다.
- AND 두 profile의 최신 catalog가 동일한 MDX 또는 navigation 경로를 current output으로 계획합니다.
- WHEN `full-all` 또는 profile conversion을 실행합니다.
- THEN 모든 profile catalog를 변환 전에 갱신해야 합니다(SHALL).
- AND 충돌 경로의 output을 생성하거나 기존 output을 덮어쓰기 전에 conversion을 오류로 종료해야 합니다(SHALL).
- AND 어느 profile의 manifest도 교체하지 않아야 합니다(SHALL NOT).

#### Scenario: unsafe manifest path

- GIVEN manifest entry가 configured output root 밖을 가리키거나 허용되지 않은 파일을 가리킵니다.
- WHEN stale cleanup을 실행합니다.
- THEN 해당 경로를 삭제하지 않아야 합니다(SHALL NOT).
- AND conversion을 오류로 종료해야 합니다(SHALL).

### Requirement: Existing profile compatibility

Typed folder 지원은 기존 page 변환과 folder root sync profile을 유지해야 합니다(SHALL).

#### Scenario: page root profile

- GIVEN QM처럼 sync root type이 `page`입니다.
- WHEN remote fetch와 conversion을 실행합니다.
- THEN 기존 page body, attachment, MDX path를 유지해야 합니다(SHALL).

#### Scenario: folder root profile

- GIVEN QCP처럼 sync root type이 `folder`입니다.
- WHEN remote fetch와 conversion을 실행합니다.
- THEN root부터 typed tree를 수집해야 합니다(SHALL).
- AND 기존 정책에 따라 sync root 자체의 MDX는 생성하지 않아야 합니다(SHALL NOT).
