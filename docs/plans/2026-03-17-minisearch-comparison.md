# MiniSearch 기반 검색 구현 및 전환 계획

> **Status:** ✅ 완료 (PR #925 구현 + PR #927 기반 정리)

**Goal:** MiniSearch(BM25+) 기반 검색을 `/mcp` 엔드포인트에 추가하고, 기존 커스텀 검색 엔진과 비교 평가 후 MiniSearch로 완전 전환합니다.

**최종 아키텍처:** MiniSearch 인덱스를 빌드 시점에 `{lang}-minisearch.json`으로 생성합니다. 런타임에 `search_docs` MCP tool은 MiniSearch(BM25+)만 사용합니다.

**Tech Stack:** `minisearch` npm 패키지, `Intl.Segmenter` (Node.js 내장, 한국어/일본어 토크나이저), TypeScript

---

## 최종 파일 구조

### 신규 생성 (PR #925)

| 파일 | 역할 |
|------|------|
| `src/lib/doc-search/minisearch-engine.ts` | MiniSearch 인스턴스 생성, 인덱스 로드, `searchWithMiniSearch()` 함수 |
| `src/lib/doc-search/__tests__/minisearch-engine.test.ts` | MiniSearch 엔진 단위 테스트 |
| `scripts/build-doc-search-index/build-minisearch.ts` | 청크 데이터를 MiniSearch JSON 인덱스로 직렬화 |
| `scripts/build-doc-search-index/__tests__/build-minisearch.test.ts` | 인덱스 빌드 단위 테스트 |
| `public/_doc-search/{lang}-minisearch.json` | MiniSearch 직렬화 인덱스 (ko/en/ja) |

### 제거 (PR #928 커스텀 엔진 정리)

| 파일 | 이유 |
|------|------|
| `src/lib/doc-search/search.ts` | 커스텀 검색 엔진 — MiniSearch로 대체 |
| `src/lib/doc-search/__tests__/search.test.ts` | 위 파일의 테스트 |
| `public/_doc-search/{lang}-index.json` | 커스텀 엔진 전용 인덱스 파일 — 불필요 |

### 수정

| 파일 | 변경 내용 |
|------|-----------|
| `package.json` | `dependencies`에 `minisearch` 추가 |
| `src/lib/doc-search/types.ts` | `SearchEngine`, `ComparisonResult` 제거; `SearchDocsParams.artifact` 제거 |
| `src/lib/doc-search/mcp.ts` | `searchEngine` 파라미터 제거, MiniSearch 단독 사용 |
| `src/lib/doc-search/load-index.ts` | `loadDocSearchArtifact` 제거 (커스텀 엔진 전용) |
| `scripts/build-doc-search-index/index.ts` | `{lang}-index.json` 출력 제거 |

---

## Phase 1: MiniSearch 구현 및 비교 (PR #925) ✅

### 구현 내용

1. `minisearch` 의존성 추가
2. `minisearch-engine.ts` — `Intl.Segmenter` 기반 토크나이저, BM25+ 검색
3. `build-minisearch.ts` — 빌드 시 MiniSearch 인덱스 직렬화
4. `load-index.ts` — `loadMiniSearchIndex()` 추가
5. `mcp.ts` — `search_docs` tool에 `searchEngine` 파라미터 추가 (`custom` | `minisearch` | `both`)

### 비교 평가 결과 (issue #927)

- **응답 속도**: MiniSearch 평균 3.33ms vs Custom 32.61ms → **9.8배 빠름**
- **검색 품질**: 2단어 이상 쿼리에서 MiniSearch 우세 또는 동등
- **결론**: MiniSearch(BM25+)로 완전 전환 결정

---

## Phase 2: 커스텀 엔진 제거 (PR #928) ✅

### 구현 내용

1. `search.ts`, `search.test.ts` 삭제
2. `{lang}-index.json` 파일 삭제
3. `types.ts` — `SearchEngine`, `ComparisonResult`, `SearchDocsParams.artifact` 제거
4. `mcp.ts` — `searchEngine` 파라미터 제거, MiniSearch 단독 사용
5. `load-index.ts` — `loadDocSearchArtifact` 제거
6. `scripts/build-doc-search-index/index.ts` — `{lang}-index.json` 출력 제거
7. 테스트 업데이트

---

## 검증 방법

```bash
# 인덱스 빌드
npm run build-doc-search-index

# 테스트
npm run test:run

# 개발 서버 실행 후 MCP Inspector로 search_docs 호출 확인
npm run dev
```
