# Reverse-Sync Push 안전장치 설계

## 배경

`reverse-sync push` 명령은 MDX 교정 결과를 Confluence에 반영합니다.
현재 `_do_push()`는 최소 구현으로, 프로덕션 사용에 필요한 안전장치가 없습니다:

- 버전 충돌 시 무조건 실패 (에러 메시지 불명확)
- 확인 없이 즉시 push
- 원본 백업 없음

## 범위

3가지 안전장치를 추가합니다:

1. **버전 충돌 감지** (Optimistic Locking)
2. **확인 프롬프트** + `--yes` 플래그
3. **원본 백업**

## 설계

### 1. 버전 충돌 감지

Confluence REST API의 version number 기반 optimistic locking에 의존합니다.

- `update_page_body()` 호출 시 409 응답을 `requests.HTTPError`로 catch
- 409인 경우 명확한 에러 메시지 출력:
  "페이지가 Confluence에서 변경되었습니다. fetch로 최신 버전을 가져온 후 다시 시도하세요."
- 배치 모드에서는 해당 페이지만 `conflict` 상태로 기록하고 나머지 계속 진행

### 2. 확인 프롬프트 + `--yes` 플래그

- **단일 파일 push**: push 직전에 `Push <title> (v<N>) to Confluence? [y/N]` 프롬프트
- **배치 push**: verify 전체 완료 후 pass 건수 요약 → `N건을 push 할까요? [y/N]` 한 번 확인
- `--yes` 옵션: 프롬프트 스킵 (CI/자동화용)
- `--dry-run`은 기존대로 push 자체를 안 함 (프롬프트도 안 뜸)

배치 모드 흐름 변경:

```
Before: verify → pass이면 즉시 push (페이지별)
After:  verify 전체 → 요약 출력 → 확인 → pass 건만 일괄 push
```

### 3. 원본 백업

- push 직전에 Confluence에서 현재 XHTML body를 조회
- `var/<page_id>/reverse-sync.backup.xhtml`에 저장
- 충돌/실패 시 수동 복원 참고용 (자동 롤백은 안 함)

## 변경 파일

### `confluence-mdx/bin/reverse_sync/confluence_client.py`

- `get_page_body(config, page_id)` 함수 추가: 현재 XHTML body 반환

### `confluence-mdx/bin/reverse_sync_cli.py`

- `_do_push()`: 백업 저장 + 409 에러 핸들링
- `_do_verify_batch()`: verify-then-push 분리, 확인 프롬프트
- `_do_push_single()`: 단일 파일 push에 확인 프롬프트 추가
- argparse: `--yes` 옵션 추가

## 변경하지 않는 것

- verify 로직, sidecar, patch_builder 등 기존 파이프라인
- 자동 롤백, 배치 중단/재개
