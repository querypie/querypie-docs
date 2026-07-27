# contract-reverse-sync

## Purpose

MDX 변경을 기존 Confluence Storage XHTML의 보존 정보와 안전하게 결합하고, 검증한 원격 page snapshot에만 반영하며, 저장된 결과가 target MDX와 동등함을 증명하는 durable contract를 정의합니다.

## References

- `openspec/changes/complete-reverse-sync/proposal.md`
- `openspec/changes/complete-reverse-sync/design.md`
- `confluence-mdx/docs/architecture.md`
- `confluence-mdx/bin/reverse_sync_cli.py`
- `confluence-mdx/bin/reverse_sync/**`
- [Confluence Cloud REST API v2 Page](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/)
- [Confluence Cloud REST API v2 Attachment](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-attachment/)

## ADDED Requirements

### Requirement: Consistent PageSnapshot

reverse-sync는 Confluence page의 `page_id`, `status`, `title`, `version`, Storage XHTML을 하나의 논리적으로 일관된 `PageSnapshot`으로 획득하고 Storage XHTML의 SHA-256을 기록해야 합니다(SHALL).

version과 body를 서로 다른 시점의 독립 조회에서 가져와 하나의 snapshot으로 조합해서는 안 됩니다(SHALL NOT).

#### Scenario: 원격 current page snapshot 획득

- GIVEN 사용자가 reverse-sync prepare 또는 online verify를 실행합니다.
- WHEN 도구가 Confluence current page를 조회합니다.
- THEN 하나의 API response 또는 동일 version을 명시한 조회에서 page ID, status, title, version, Storage XHTML을 획득해야 합니다(SHALL).
- AND body hash와 fetch 시각, API adapter version을 snapshot에 기록해야 합니다(SHALL).

#### Scenario: offline XHTML 입력

- GIVEN 사용자가 snapshot metadata가 없는 로컬 `page.xhtml`로 verify합니다.
- WHEN local round-trip이 통과합니다.
- THEN 도구는 진단 결과를 제공할 수 있습니다(MAY).
- AND 결과를 push eligible로 표시해서는 안 됩니다(SHALL NOT).

#### Scenario: snapshot field 불일치

- GIVEN API response의 page ID, status, representation, version 중 필수 필드가 없거나 요청과 다릅니다.
- WHEN snapshot adapter가 response를 파싱합니다.
- THEN 도구는 `invalid_page_snapshot`으로 block해야 합니다(SHALL).
- AND 불완전한 snapshot으로 patch 또는 push를 계속해서는 안 됩니다(SHALL NOT).

### Requirement: Base Parity

reverse-sync는 patch를 push eligible로 판정하기 전에 base snapshot을 forward conversion한 canonical MDX와 original MDX의 page identity 및 content 동등성을 확인해야 합니다(SHALL).

#### Scenario: base와 original MDX가 대응함

- GIVEN `PageSnapshot B`와 original MDX `O`가 있습니다.
- WHEN `B.storage_xhtml`을 현재 forward converter와 동일한 dependency catalog로 변환합니다.
- THEN 변환 결과와 `O`의 page ID, `confluenceUrl`, content가 push equivalence policy에서 일치해야 합니다(SHALL).
- AND 사용한 converter/tool version과 입력 hash를 manifest에 기록해야 합니다(SHALL).

#### Scenario: repository source identity

- GIVEN original/improved MDX와 current `PageSnapshot B`가 있습니다.
- WHEN source identity를 검증합니다.
- THEN 두 MDX descriptor는 같은 `src/content/ko/**.mdx` path를 가리켜야 합니다(SHALL).
- AND 해당 path, `B.page_id`, 두 MDX의 `confluenceUrl` page ID가 page catalog의 유일한 row에서 일치해야 합니다(SHALL).
- AND 하나라도 없거나 중복되거나 다르면 `page_identity_mismatch`로 block해야 합니다(SHALL).

#### Scenario: stale original MDX

- GIVEN 원격 base snapshot에는 original MDX에 없는 content가 있습니다.
- WHEN base parity를 검증합니다.
- THEN 결과는 `stale_original_mdx` 또는 `base_parity_mismatch`로 block되어야 합니다(SHALL).
- AND reverse-sync는 원격 content를 target MDX로 조용히 덮어써서는 안 됩니다(SHALL NOT).

#### Scenario: converter drift

- GIVEN 동일한 Storage XHTML이 converter 변경으로 과거 original MDX와 다르게 변환됩니다.
- WHEN base parity를 검증합니다.
- THEN 결과는 일반 patch mismatch와 구분되는 `forward_converter_drift` evidence를 포함해야 합니다(SHALL).
- AND reviewer가 equivalence policy 또는 original MDX를 갱신하기 전까지 push eligible이 되어서는 안 됩니다(SHALL NOT).

### Requirement: Intent-Complete Patch Plan

reverse-sync는 original MDX `O`와 improved MDX `I`의 모든 변경을 provenance가 확인된 base XHTML fragment에 대응시키는 deterministic patch plan을 생성해야 합니다(SHALL).

모호한 identity, unsupported capability, skipped change가 존재하는 plan을 verified로 판정해서는 안 됩니다(SHALL NOT).

#### Scenario: 지원되는 block 변경

- GIVEN original/improved MDX 사이에 지원되는 paragraph 변경이 있습니다.
- AND original block은 base snapshot의 exact fragment identity를 가집니다.
- WHEN planner가 변경을 분석합니다.
- THEN 변경은 정확히 하나의 capability와 target fragment, operation에 대응해야 합니다(SHALL).
- AND plan은 old/new block hash와 target fragment hash를 포함해야 합니다(SHALL).

#### Scenario: 중복 block의 target이 모호함

- GIVEN 동일한 content를 가진 block이 여러 개이고 provenance로 target을 하나로 확정할 수 없습니다.
- WHEN planner가 target을 결정합니다.
- THEN `ambiguous_target`으로 block해야 합니다(SHALL).
- AND normalized text prefix만으로 임의의 target을 선택해서는 안 됩니다(SHALL NOT).

#### Scenario: unsupported 구조 변경

- GIVEN improved MDX가 preserved macro 또는 raw HTML table의 지원되지 않는 구조를 변경합니다.
- WHEN planner가 capability를 분류합니다.
- THEN `unsupported_capability`과 capability ID를 반환해야 합니다(SHALL).
- AND patch를 일부만 적용하거나 skipped change를 success로 숨겨서는 안 됩니다(SHALL NOT).

#### Scenario: insert와 delete

- GIVEN improved MDX가 block을 추가하거나 삭제합니다.
- WHEN planner가 operation을 생성합니다.
- THEN insert는 stable neighbor identity를, delete는 exact base fragment identity를 가져야 합니다(SHALL).
- AND 필요한 identity가 없으면 `missing_identity`로 block해야 합니다(SHALL).

### Requirement: Preserve Unmodeled XHTML

reverse-sync는 MDX 변경 의도에 포함되지 않은 document envelope, separator, fragment, macro parameter, local ID, attachment metadata를 byte-preserving 방식으로 유지해야 합니다(SHALL).

#### Scenario: unchanged fragment

- GIVEN base snapshot의 한 fragment에 대응하는 MDX block이 변경되지 않았습니다.
- WHEN candidate XHTML을 생성합니다.
- THEN 해당 fragment bytes와 인접 separator는 base snapshot과 같아야 합니다(SHALL).

#### Scenario: template-preserving edit

- GIVEN changed paragraph가 Confluence link 또는 attachment preservation unit을 포함합니다.
- AND capability가 visible text 변경만 지원합니다.
- WHEN renderer가 candidate fragment를 생성합니다.
- THEN 원본 wrapper와 preservation unit의 target/metadata를 유지하고 승인된 visible segment만 변경해야 합니다(SHALL).

#### Scenario: preservation proof 부족

- GIVEN renderer가 unmodeled markup을 안전하게 보존했는지 증명할 수 없습니다.
- WHEN candidate fragment를 검증합니다.
- THEN `preservation_uncertain` 또는 `preservation_mismatch`로 block해야 합니다(SHALL).

### Requirement: Strict Local Proof

reverse-sync는 candidate XHTML을 push eligible로 표시하기 전에 source identity, base parity, intent completeness, artifact integrity, XHTML well-formedness, unchanged fragment preservation, semantic round-trip, determinism, idempotency, dependency gate를 모두 통과해야 합니다(SHALL).

#### Scenario: local proof 통과

- GIVEN plan의 모든 operation이 candidate XHTML에 적용되었습니다.
- WHEN local proof를 실행합니다.
- THEN candidate XHTML의 forward conversion 결과는 improved MDX와 versioned push equivalence policy에서 동등해야 합니다(SHALL).
- AND 모든 필수 gate가 `pass`이고 blocked reason이 없을 때만 상태를 `verified_local`로 설정해야 합니다(SHALL).

#### Scenario: skipped change

- GIVEN patch engine이 하나 이상의 MDX 변경을 skip했습니다.
- WHEN local proof 결과를 조립합니다.
- THEN `intent_complete` gate는 실패해야 합니다(SHALL).
- AND round-trip normalization이 우연히 일치하더라도 push eligible이 되어서는 안 됩니다(SHALL NOT).

#### Scenario: lenient match

- GIVEN strict push equivalence는 실패하지만 `--lenient` 비교는 통과합니다.
- WHEN 결과를 출력합니다.
- THEN diagnostic match와 strict failure를 함께 보고할 수 있습니다(MAY).
- AND 상태를 `verified_local`로 설정해서는 안 됩니다(SHALL NOT).

#### Scenario: title normalization

- GIVEN original/improved MDX의 title 또는 첫 H1이 다릅니다.
- WHEN body reverse-sync proof를 실행합니다.
- THEN title을 비교에서 제거하여 success로 만들지 않고 `title_change_unsupported`로 block해야 합니다(SHALL).

### Requirement: Immutable SyncManifest

reverse-sync는 base snapshot, original/improved MDX, patch plan, candidate XHTML, verifier policy, tool version의 hash를 포함하는 실행별 `SyncManifest`를 생성해야 합니다(SHALL).

push는 verified manifest가 가리키는 candidate만 사용할 수 있습니다(SHALL).
publisher는 verified manifest를 수정하지 않고 manifest hash를 참조하는 별도 push receipt와 post-snapshot을 기록해야 합니다(SHALL).

#### Scenario: verify 후 push

- GIVEN local proof를 통과한 manifest가 있습니다.
- WHEN publisher가 push를 준비합니다.
- THEN manifest와 모든 referenced artifact의 hash를 다시 계산해야 합니다(SHALL).
- AND hash가 모두 일치할 때만 remote preflight로 진행해야 합니다(SHALL).

#### Scenario: candidate artifact 변경

- GIVEN verify 후 candidate XHTML이 수정되었습니다.
- WHEN publisher가 manifest integrity를 검증합니다.
- THEN `artifact_tampered`로 block해야 합니다(SHALL).
- AND 수정된 body를 PUT해서는 안 됩니다(SHALL NOT).

#### Scenario: verifier policy 변경

- GIVEN manifest가 기록한 verifier policy 또는 tool version이 현재 publisher가 허용한 version과 다릅니다.
- WHEN publisher가 artifact를 로드합니다.
- THEN 재검증을 요구하거나 `stale_verification`으로 block해야 합니다(SHALL).

### Requirement: Remote Compare-And-Set

publisher는 PUT 직전에 원격 current snapshot을 다시 획득하고, 검증에 사용한 base snapshot과 page ID, status, version, title, Storage body hash가 동일한지 확인해야 합니다(SHALL).

publisher는 preflight에서 얻은 latest version을 검증 base로 암묵적으로 승격해서는 안 됩니다(SHALL NOT).

#### Scenario: remote가 base와 동일함

- GIVEN verified manifest의 base version과 body hash가 원격 current snapshot과 같습니다.
- AND active draft가 없습니다.
- WHEN publisher가 update를 요청합니다.
- THEN base version에 정확히 1을 더한 version과 manifest의 candidate body를 사용해야 합니다(SHALL).

#### Scenario: remote body drift

- GIVEN remote version 또는 body hash가 verified manifest의 base와 다릅니다.
- AND remote content가 improved MDX와 동등하지 않습니다.
- WHEN publisher가 preflight합니다.
- THEN `remote_drift`로 block해야 합니다(SHALL).
- AND PUT을 호출해서는 안 됩니다(SHALL NOT).

#### Scenario: preflight와 PUT 사이의 race

- GIVEN preflight 후 다른 사용자가 page를 갱신했습니다.
- WHEN publisher가 base version + 1로 update합니다.
- THEN API conflict를 `version_conflict`로 분류해야 합니다(SHALL).
- AND 최신 version을 다시 읽어 같은 candidate를 자동 재시도해서는 안 됩니다(SHALL NOT).

#### Scenario: active draft

- GIVEN page에 current version과 다른 active draft가 있습니다.
- WHEN publisher가 preflight합니다.
- THEN `active_draft`로 block해야 합니다(SHALL).
- AND 명시적으로 승인된 draft reconciliation capability가 없으면 current page update를 수행해서는 안 됩니다(SHALL NOT).

### Requirement: Remote Postcondition

publisher는 update 응답을 성공의 최종 증거로 취급하지 않고 persisted remote snapshot을 다시 조회하여 version과 semantic target을 검증해야 합니다(SHALL).

#### Scenario: persisted result 검증

- GIVEN Confluence update API가 성공을 반환했습니다.
- WHEN publisher가 current page를 다시 조회합니다.
- THEN persisted version은 base version + 1이어야 합니다(SHALL).
- AND persisted Storage XHTML의 forward conversion 결과는 improved MDX와 push equivalence policy에서 동등해야 합니다(SHALL).
- AND 통과한 경우에만 상태를 `remote_verified`로 설정해야 합니다(SHALL).

#### Scenario: persisted body mismatch

- GIVEN update API는 성공했지만 persisted body가 target MDX와 동등하지 않습니다.
- WHEN postcondition을 검증합니다.
- THEN 상태를 `postcondition_failed`로 기록해야 합니다(SHALL).
- AND base snapshot, attempted candidate, persisted snapshot, response version을 recovery evidence로 보존해야 합니다(SHALL).
- AND 후속 batch push를 기본적으로 중단해야 합니다(SHALL).

#### Scenario: 이미 적용된 target

- GIVEN remote snapshot이 base와 다르지만 이미 improved MDX와 semantic equivalent입니다.
- WHEN 사용자가 동일한 intent를 다시 실행합니다.
- THEN PUT을 생략하고 `already_applied`로 보고할 수 있습니다(MAY).
- AND remote content가 target과 동등하다는 postcondition evidence를 기록해야 합니다(SHALL).

### Requirement: Explicit Dependency Boundaries

reverse-sync는 body에 새로 추가되는 attachment와 internal page dependency를 명시적 catalog 및 preflight gate로 검증해야 합니다(SHALL).

첫 reverse-sync completion 범위는 body content update로 제한하며 title 변경,
attachment upload/update/delete lifecycle, unresolved link를 암묵적으로
처리해서는 안 됩니다(SHALL NOT).

#### Scenario: title 변경

- GIVEN improved MDX가 frontmatter title 또는 page title H1을 변경합니다.
- WHEN planner가 변경을 분석합니다.
- THEN `title_change_unsupported`로 block해야 합니다(SHALL).

#### Scenario: 존재하지 않는 attachment 참조

- GIVEN improved MDX가 base page에 존재하지 않는 attachment filename을 참조합니다.
- WHEN dependency gate를 실행합니다.
- THEN `missing_attachment`로 block해야 합니다(SHALL).
- AND broken `ri:attachment` 참조를 포함한 body를 push해서는 안 됩니다(SHALL NOT).

#### Scenario: 기존 attachment의 새 reference

- GIVEN improved MDX가 current attachment catalog에 유일하게 존재하는 filename을 새로 참조합니다.
- WHEN dependency gate와 candidate renderer를 실행합니다.
- THEN attachment ID, filename, version, catalog hash를 local proof에 기록해야 합니다(SHALL).
- AND candidate는 해당 filename을 가진 `ri:attachment` reference를 생성해야 합니다(SHALL).
- AND attachment upload 또는 version 변경을 암묵적으로 실행해서는 안 됩니다(SHALL NOT).

#### Scenario: unresolved internal link

- GIVEN link resolver가 target page를 하나로 결정하지 못합니다.
- WHEN candidate XHTML을 생성합니다.
- THEN target이 없으면 `internal_link_unresolved`, 여러 target이면 `ambiguous_target`으로 block해야 합니다(SHALL).
- AND unresolved relative anchor를 일반 HTML link로 조용히 남겨서는 안 됩니다(SHALL NOT).

#### Scenario: resolved internal link

- GIVEN improved MDX의 새 relative link가 page catalog의 유일한 page ID/path와 일치합니다.
- WHEN candidate XHTML을 생성합니다.
- THEN target page ID/title/href를 local proof에 기록해야 합니다(SHALL).
- AND candidate는 target title을 가진 Confluence `ac:link`/`ri:page` macro를 생성해야 합니다(SHALL).

#### Scenario: dependency preflight drift

- GIVEN local proof가 attachment filename 또는 internal page ID/title을 요구합니다.
- AND verify 이후 attachment가 사라지거나 linked page가 rename/delete되었습니다.
- WHEN publisher가 PUT 직전 dependency preflight를 실행합니다.
- THEN `dependency_failure`로 block해야 합니다(SHALL).
- AND PUT을 호출해서는 안 됩니다(SHALL NOT).

### Requirement: Page-Scoped Batch Semantics

batch reverse-sync는 각 page를 독립 transaction으로 처리하고 전체 batch가 원자적인 것처럼 보고해서는 안 됩니다(SHALL NOT).

#### Scenario: batch local proof

- GIVEN branch에 여러 MDX page 변경이 있습니다.
- WHEN batch verify를 실행합니다.
- THEN 모든 page의 local proof를 push 전에 완료하고 verified/blocked manifest를 구분해야 합니다(SHALL).

#### Scenario: batch partial success

- GIVEN 첫 page는 `remote_verified`이고 두 번째 page는 `remote_drift`입니다.
- WHEN batch push가 종료됩니다.
- THEN 첫 page의 성공을 rollback된 것처럼 표시해서는 안 됩니다(SHALL NOT).
- AND 전체 상태를 partial success로 표시하고 page별 상태를 반환해야 합니다(SHALL).

#### Scenario: postcondition failure

- GIVEN batch 중 한 page가 `postcondition_failed`가 되었습니다.
- WHEN 다음 page를 처리하려고 합니다.
- THEN 기본 동작은 남은 push를 중단해야 합니다(SHALL).
- AND 사용자가 별도 실행으로 재개할 수 있는 manifest 목록을 제공해야 합니다(SHALL).

### Requirement: Recoverable and Auditable Operation

reverse-sync는 실행별 base snapshot, plan, candidate, verification, push response, post-snapshot을 보존하고 credential 또는 API token을 artifact에 기록해서는 안 됩니다(SHALL NOT).

#### Scenario: push 실패 조사

- GIVEN push가 conflict, network error, postcondition failure 중 하나로 종료되었습니다.
- WHEN maintainer가 run artifact를 확인합니다.
- THEN page ID, base/persisted version, relevant hash, reason code, 재현 가능한 local verification 정보를 확인할 수 있어야 합니다(SHALL).

#### Scenario: recovery 안내

- GIVEN postcondition failure가 발생했습니다.
- WHEN 도구가 결과를 출력합니다.
- THEN base version과 backup artifact 위치를 포함한 수동 recovery 안내를 제공해야 합니다(SHALL).
- AND current remote가 attempted candidate와 동일한지 확인하지 않은 자동 restore를 수행해서는 안 됩니다(SHALL NOT).

#### Scenario: credential redaction

- GIVEN API request/response와 error가 artifact에 기록됩니다.
- WHEN manifest와 log를 직렬화합니다.
- THEN email, API token, Authorization header를 포함해서는 안 됩니다(SHALL NOT).
