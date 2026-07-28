## 1. Contract

- [x] 1.1 현재 제목 기반 canonical route와 8주 redirect lifecycle을 change-local spec에 정의합니다.
- [x] 1.2 redirect registry schema, expiration 의미, 연속 rename 처리 방식을 design에 기록합니다.

## 2. Implementation

- [x] 2.1 content ID 기반 slug override 적용 경로와 설정을 제거합니다.
- [x] 2.2 conversion manifest의 content ID별 MDX path 변경에서 redirect를 생성합니다.
- [x] 2.3 redirect에 UTC 생성일과 기본 56일 만료일을 기록하고 만료 record를 정리합니다.
- [x] 2.4 active redirect를 locale별 Next.js 임시 redirect로 확장합니다.
- [x] 2.5 변경된 한국어 route와 영어·일본어 대응 route를 새 제목 경로로 이동합니다.

## 3. Verification

- [x] 3.1 title translation에서 새 canonical route가 생성되는 unit test를 추가합니다.
- [x] 3.2 route 이동, 56일 만료일, 만료 cleanup, 연속 rename을 Python test로 검증합니다.
- [x] 3.3 active/expired registry loading과 locale redirect 확장을 TypeScript test로 검증합니다.
- [x] 3.4 변경된 ko/en/ja 문서의 Skeleton 구조와 내부 link를 검증합니다.
- [x] 3.5 lint, converter test, Next build를 실행합니다.

## 4. Spec / 구현 drift 확인

- [x] 4.1 `content-slug-overrides` 또는 stable route 보존을 canonical 정책으로 설명하는 active guidance가 남아 있지 않은지 검색합니다.
- [x] 4.2 만료된 redirect가 runtime 설정에 포함되거나 registry cleanup에서 누락되는 경로가 없는지 확인합니다.

## 5. OpenSpec Cleanup

- [ ] 5.1 변경이 accepted되면 `platform-docs-site-routing` accepted spec inventory를 갱신합니다.
- [ ] 5.2 구현과 검증이 완료된 change를 archive합니다.
