## 1. Contract

- [x] 1.1 `proposal.md`, `design.md`, change-local `contract-confluence-mdx-conversion` spec을 reviewer와 확정합니다.
- [x] 1.2 `confluence-mdx/README.md`에 folder raw 저장 형식과 `--remote`/`--recent` hierarchy freshness 계약을 반영합니다.
- [x] 1.3 issue #1028의 “folder MDX 미생성”과 “`--recent` 즉시 hierarchy reconcile” 요구를 승인된 계약으로 교체합니다.

## 2. Implementation

- [x] 2.1 `bin/fetch/api_client.py`에 page/folder `direct-children` endpoint와 cursor pagination을 구현합니다.
- [x] 2.2 `bin/fetch/models.py`의 내부 모델을 typed `ContentNode`로 일반화하고 catalog에 `type`을 직렬화합니다.
- [x] 2.3 `bin/fetch/processor.py`의 재귀 입력이 `{id, type, title, childPosition}`을 보존하도록 변경합니다.
- [x] 2.4 `bin/fetch/stages.py`에서 folder는 `folder.v2.yaml`과 `children.v2.yaml`만 저장하고 page-only API/body/attachment stage를 실행하지 않도록 분리합니다.
- [x] 2.5 breadcrumb와 path를 parent traversal context에서 계산하여 folder가 V1 ancestor 없이 catalog에 포함되도록 변경합니다.
- [x] 2.6 `--recent`가 `children.v2.yaml`을 갱신하지 않고 저장된 hierarchy만 재사용하도록 page content fetch operation을 분리합니다.
- [x] 2.7 `bin/convert_all.py`에 deterministic folder MDX generator를 추가합니다.
- [x] 2.8 `_meta.ts` 생성을 `bin/converter/cli.py`의 XHTML side effect에서 catalog-level navigation pass로 이동합니다.
- [x] 2.9 `var/convert-manifest.<sync-code>.yaml`의 atomic update와 stale generated output 안전 삭제를 구현합니다.
- [x] 2.10 folder MDX가 reverse sync 대상이 아닐 때 명확한 오류를 반환하도록 관련 entry point를 확인하고 필요한 guard를 추가합니다.

## 3. Verification

- [x] 3.1 API client 단위 테스트에서 page/folder endpoint와 cursor 2개 이상의 pagination merge를 검증합니다.
- [x] 3.2 mixed tree fixture `page → folder → (page, nested folder → page)`로 type 보존, breadcrumb, path, ordering을 검증합니다.
- [x] 3.3 `database`, `whiteboard`, `embed`가 catalog/MDX/navigation에서 제외되고 식별 가능한 경고가 남는지 검증합니다.
- [x] 3.4 folder raw fixture에서 `folder.v2.yaml`, `children.v2.yaml`만 생성되고 page-only artifact가 생성되지 않는지 검증합니다.
- [x] 3.5 `--remote`가 hierarchy를 갱신하고 `--recent`/`--local`이 cached hierarchy를 유지하는 mode 테스트를 추가합니다.
- [x] 3.6 folder MDX의 frontmatter, H1, `## 하위 문서`, direct-child 상대 link, `childPosition` 순서를 golden test로 검증합니다.
- [x] 3.7 nested folder의 descendant가 부모 folder MDX에 펼쳐지지 않고 nested folder MDX에만 나타나는지 검증합니다.
- [x] 3.8 빈 folder가 `하위 문서가 없습니다.`를 포함한 MDX를 생성하는지 검증합니다.
- [x] 3.9 page와 folder가 섞인 `_meta.ts`가 MDX 존재 여부와 순서를 정확히 반영하는지 검증합니다.
- [x] 3.10 folder 이동·이름 변경·삭제 fixture에서 이전 manifest 소유 파일만 삭제되고 비소유 파일은 보존되는지 검증합니다.
- [x] 3.11 conversion 중간 실패 시 stale file 삭제와 manifest 교체가 일어나지 않는지 검증합니다.
- [ ] 3.12 QM 대상 folder `2167636017`과 QCP folder root profile의 smoke 결과를 확인합니다.
- [x] 3.13 focused Python test, `git diff --check`, 관련 `rg` source scan을 실행합니다.

권장 focused 명령:

```bash
cd confluence-mdx
source venv/bin/activate
pytest -q tests/test_fetch_folders.py tests/test_convert_all_folders.py
bin/fetch_cli.py --local --sync-code qm
bin/convert_all.py --sync-code qm
git diff --check
```

실제 Confluence hierarchy 확인이 필요한 smoke는 credential이 있는 환경에서 수행합니다.

```bash
bin/fetch_cli.py --remote --sync-code qm --start-page-id 544178405
bin/convert_all.py --sync-code qm
```

## 4. Spec / 구현 drift 확인

- [x] 4.1 `pages.<code>.yaml`을 읽는 모든 consumer가 추가된 `type` 필드를 무시하거나 올바르게 사용하는지 source scan합니다.
- [x] 4.2 `_meta.ts`를 생성하는 다른 code path가 남아 중복 write하지 않는지 확인합니다.
- [x] 4.3 README, CLI help, sync profile 설명에서 `--recent`를 full hierarchy sync처럼 설명하는 stale 문구가 없는지 확인합니다.
- [x] 4.4 folder MDX가 translation/skeleton/reverse-sync workflow에서 일반 page body로 잘못 취급되지 않는지 확인합니다.
- [x] 4.5 manifest cleanup이 sync code가 다른 출력이나 attachment를 삭제하지 않는지 확인합니다.

## 5. OpenSpec Cleanup

- [ ] 5.1 구현과 검증이 완료되면 `contract-confluence-mdx-conversion`을 `openspec/specs/`에 accepted spec으로 반영합니다.
- [ ] 5.2 `openspec/specs/README.md` inventory를 갱신합니다.
- [ ] 5.3 완료된 change를 `openspec/archive/<date>-confluence-folder-mdx/`로 이동합니다.
