# MiniSearch 기반 검색 비교 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 커스텀 검색(고정 가중치 스코어링)과 MiniSearch(BM25+) 기반 검색을 `/mcp` 엔드포인트에 나란히 추가하여 검색 품질과 성능을 비교할 수 있게 합니다.

**Architecture:** MiniSearch 인덱스를 빌드 시점에 별도 JSON 파일(`{lang}-minisearch.json`)로 생성합니다. 런타임에 `search_docs` MCP tool의 `searchEngine` 파라미터(`custom` | `minisearch` | `both`)로 엔진을 선택할 수 있으며, `both` 선택 시 두 결과를 나란히 반환하여 직접 비교합니다.

**Tech Stack:** `minisearch` npm 패키지, `Intl.Segmenter` (Node.js 내장, 한국어/일본어 토크나이저), TypeScript

---

## 파일 구조

### 신규 생성

| 파일 | 역할 |
|------|------|
| `src/lib/doc-search/minisearch-engine.ts` | MiniSearch 인스턴스 생성, 인덱스 로드, `searchWithMiniSearch()` 함수 |
| `src/lib/doc-search/__tests__/minisearch-engine.test.ts` | MiniSearch 엔진 단위 테스트 |
| `scripts/build-doc-search-index/build-minisearch.ts` | 청크 데이터를 MiniSearch JSON 인덱스로 직렬화 |
| `scripts/build-doc-search-index/__tests__/build-minisearch.test.ts` | 인덱스 빌드 단위 테스트 |

### 수정

| 파일 | 변경 내용 |
|------|-----------|
| `package.json` | `dependencies`에 `minisearch` 추가 |
| `scripts/build-doc-search-index/index.ts` | MiniSearch 인덱스 빌드를 `writeDocSearchArtifacts()`에 통합 |
| `src/lib/doc-search/mcp.ts` | `search_docs` tool에 `searchEngine` 파라미터 추가, `both` 응답 구조 추가 |
| `src/lib/doc-search/types.ts` | `SearchEngine` 타입, `ComparisonResult` 인터페이스 추가 |
| `docs/plans/README.md` (신규) | `docs/plans/` 디렉토리 인덱스 |

---

## Chunk 1: 의존성 설치 및 타입 정의

### Task 1: minisearch 설치 및 타입 추가

**Files:**
- Modify: `package.json`
- Modify: `src/lib/doc-search/types.ts`

- [ ] **Step 1: minisearch 설치**

```bash
cd /path/to/querypie-docs
npm install minisearch
```

Expected: `package.json`의 `dependencies`에 `"minisearch": "^7.x"` 추가됨

- [ ] **Step 2: types.ts에 타입 추가**

`src/lib/doc-search/types.ts` 끝에 추가:

```ts
export type SearchEngine = 'custom' | 'minisearch' | 'both';

export interface SearchEngineResult {
  engine: 'custom' | 'minisearch';
  results: DocSearchChunk[];
  durationMs: number;
}

export interface ComparisonResult {
  custom: SearchEngineResult;
  minisearch: SearchEngineResult;
}
```

- [ ] **Step 3: 테스트 실행 — 기존 테스트 깨지지 않는지 확인**

```bash
npm run test:run
```

Expected: `56 passed`

- [ ] **Step 4: 커밋**

```bash
git add package.json package-lock.json src/lib/doc-search/types.ts
git commit -m "feat(doc-search): minisearch 의존성 추가 및 비교 타입 정의합니다"
```

---

## Chunk 2: MiniSearch 엔진 구현

### Task 2: 토크나이저 및 MiniSearch 인스턴스 팩토리

**Files:**
- Create: `src/lib/doc-search/minisearch-engine.ts`
- Create: `src/lib/doc-search/__tests__/minisearch-engine.test.ts`

- [ ] **Step 1: 실패하는 테스트 작성**

`src/lib/doc-search/__tests__/minisearch-engine.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { buildMiniSearchInstance, searchWithMiniSearch } from '@/lib/doc-search/minisearch-engine';
import type { DocSearchChunk } from '@/lib/doc-search/types';

const sampleChunks: DocSearchChunk[] = [
  {
    id: 'chunk-1',
    pagePath: 'administrator-manual/databases/monitoring',
    url: '/ko/administrator-manual/databases/monitoring',
    title: 'Monitoring',
    description: '모니터링 기능',
    headingPath: ['Monitoring', 'Running Queries'],
    content: 'Running Queries 기능을 통해 실행 중인 쿼리를 확인하고 강제 중지할 수 있습니다.',
    excerpt: 'Running Queries 기능을 통해 실행 중인 쿼리를 확인하고 강제 중지할 수 있습니다.',
    metadata: {
      lang: 'ko',
      manualType: 'administrator-manual',
      productArea: 'databases',
      versionHints: [],
      isUnreleased: false,
    },
  },
  {
    id: 'chunk-2',
    pagePath: 'administrator-manual/databases/connection',
    url: '/ko/administrator-manual/databases/connection',
    title: 'Connection Management',
    description: '연결 관리',
    headingPath: ['Connection Management'],
    content: '데이터베이스 연결을 등록하고 관리합니다.',
    excerpt: '데이터베이스 연결을 등록하고 관리합니다.',
    metadata: {
      lang: 'ko',
      manualType: 'administrator-manual',
      productArea: 'databases',
      versionHints: [],
      isUnreleased: false,
    },
  },
];

describe('buildMiniSearchInstance', () => {
  it('builds an instance and finds Korean query', () => {
    const ms = buildMiniSearchInstance(sampleChunks);
    const results = ms.search('쿼리');
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].id).toBe('chunk-1');
  });

  it('finds by English term in title', () => {
    const ms = buildMiniSearchInstance(sampleChunks);
    const results = ms.search('Monitoring');
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].id).toBe('chunk-1');
  });

  it('returns empty for unrelated query', () => {
    const ms = buildMiniSearchInstance(sampleChunks);
    const results = ms.search('존재하지않는용어xyz');
    expect(results.length).toBe(0);
  });
});

describe('searchWithMiniSearch', () => {
  it('returns SearchEngineResult with durationMs', () => {
    const ms = buildMiniSearchInstance(sampleChunks);
    const result = searchWithMiniSearch(ms, { artifact: { version: 1, generatedAt: '', lang: 'ko', chunks: sampleChunks }, query: '쿼리', topK: 5 });
    expect(result.engine).toBe('minisearch');
    expect(result.durationMs).toBeGreaterThanOrEqual(0);
    expect(result.results.length).toBeGreaterThan(0);
  });

  it('respects topK limit', () => {
    const ms = buildMiniSearchInstance(sampleChunks);
    const result = searchWithMiniSearch(ms, { artifact: { version: 1, generatedAt: '', lang: 'ko', chunks: sampleChunks }, query: '관리', topK: 1 });
    expect(result.results.length).toBeLessThanOrEqual(1);
  });

  it('applies manualType filter', () => {
    const ms = buildMiniSearchInstance(sampleChunks);
    const result = searchWithMiniSearch(ms, {
      artifact: { version: 1, generatedAt: '', lang: 'ko', chunks: sampleChunks },
      query: '연결',
      topK: 5,
      manualType: 'user-manual',
    });
    expect(result.results.length).toBe(0);
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npm run test:run -- src/lib/doc-search/__tests__/minisearch-engine.test.ts
```

Expected: FAIL — `Cannot find module '@/lib/doc-search/minisearch-engine'`

- [ ] **Step 3: minisearch-engine.ts 구현**

`src/lib/doc-search/minisearch-engine.ts`:

```ts
import MiniSearch from 'minisearch';

import type { DocSearchChunk, SearchDocsParams, SearchEngineResult } from '@/lib/doc-search/types';

// Intl.Segmenter를 사용한 한국어/일본어/영어 공용 토크나이저
// Node.js 16+에 내장되어 있어 추가 의존성이 필요 없습니다.
function segmentText(text: string): string[] {
  const tokens: string[] = [];
  for (const locale of ['ko', 'ja', 'en']) {
    try {
      const segmenter = new Intl.Segmenter(locale, { granularity: 'word' });
      for (const { segment, isWordLike } of segmenter.segment(text)) {
        if (isWordLike && segment.trim().length > 0) {
          tokens.push(segment.toLowerCase());
        }
      }
      break; // 첫 번째 성공한 locale 사용
    } catch {
      continue;
    }
  }
  // fallback: 공백 분리
  if (tokens.length === 0) {
    return text.toLowerCase().split(/\s+/).filter(Boolean);
  }
  return tokens;
}

export function buildMiniSearchInstance(chunks: DocSearchChunk[]): MiniSearch<DocSearchChunk> {
  const ms = new MiniSearch<DocSearchChunk>({
    idField: 'id',
    fields: ['title', 'headingText', 'content'],
    storeFields: ['id', 'pagePath', 'url', 'title', 'description', 'headingPath', 'content', 'excerpt', 'metadata'],
    tokenize: segmentText,
    processTerm: term => term.toLowerCase(),
    searchOptions: {
      boost: { title: 3, headingText: 2, content: 1 },
      fuzzy: 0.1,
      prefix: true,
    },
  });

  // headingPath 배열을 단일 문자열 필드로 변환하여 인덱싱
  const docs = chunks.map(chunk => ({
    ...chunk,
    headingText: chunk.headingPath.join(' '),
  }));

  ms.addAll(docs);
  return ms;
}

export function searchWithMiniSearch(
  ms: MiniSearch<DocSearchChunk>,
  params: SearchDocsParams,
): SearchEngineResult {
  const { query, topK = 5, manualType } = params;
  const start = performance.now();

  const rawResults = ms.search(query);
  const filtered = manualType
    ? rawResults.filter(r => (r as unknown as DocSearchChunk).metadata?.manualType === manualType)
    : rawResults;

  const results = filtered
    .slice(0, Math.min(topK, 10))
    .map(r => r as unknown as DocSearchChunk);

  return {
    engine: 'minisearch',
    results,
    durationMs: Math.round((performance.now() - start) * 100) / 100,
  };
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npm run test:run -- src/lib/doc-search/__tests__/minisearch-engine.test.ts
```

Expected: `6 passed`

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
npm run test:run
```

Expected: `62 passed` (기존 56 + 신규 6)

- [ ] **Step 6: 커밋**

```bash
git add src/lib/doc-search/minisearch-engine.ts src/lib/doc-search/__tests__/minisearch-engine.test.ts
git commit -m "feat(doc-search): MiniSearch BM25+ 엔진 구현 및 테스트를 추가합니다"
```

---

## Chunk 3: MiniSearch 인덱스 빌드

### Task 3: 빌드 스크립트에 MiniSearch 인덱스 직렬화 추가

**Files:**
- Create: `scripts/build-doc-search-index/build-minisearch.ts`
- Create: `scripts/build-doc-search-index/__tests__/build-minisearch.test.ts`
- Modify: `scripts/build-doc-search-index/index.ts`

MiniSearch 인스턴스는 `JSON.stringify(ms)`로 직렬화할 수 있으며, `MiniSearch.loadJSON(json, options)`으로 복원됩니다.
직렬화된 파일은 `public/_doc-search/{lang}-minisearch.json`에 저장합니다.

- [ ] **Step 1: 실패하는 테스트 작성**

`scripts/build-doc-search-index/__tests__/build-minisearch.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import MiniSearch from 'minisearch';
import { serializeMiniSearchIndex } from '../build-minisearch';
import type { DocSearchChunk } from '@/lib/doc-search/types';

const sampleChunks: DocSearchChunk[] = [
  {
    id: 'test-chunk',
    pagePath: 'user-manual/getting-started',
    url: '/ko/user-manual/getting-started',
    title: 'Getting Started',
    description: '시작하기',
    headingPath: ['Getting Started'],
    content: '쿼리파이를 시작하는 방법을 안내합니다.',
    excerpt: '쿼리파이를 시작하는 방법을 안내합니다.',
    metadata: {
      lang: 'ko',
      manualType: 'user-manual',
      productArea: 'getting-started',
      versionHints: [],
      isUnreleased: false,
    },
  },
];

describe('serializeMiniSearchIndex', () => {
  it('produces a JSON string that can be loaded back', () => {
    const json = serializeMiniSearchIndex(sampleChunks);
    expect(typeof json).toBe('string');
    expect(() => JSON.parse(json)).not.toThrow();
  });

  it('loaded index can search the original content', () => {
    const json = serializeMiniSearchIndex(sampleChunks);
    const ms = MiniSearch.loadJSON<DocSearchChunk>(json, {
      fields: ['title', 'headingText', 'content'],
    });
    const results = ms.search('쿼리파이');
    expect(results.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npm run test:run -- scripts/build-doc-search-index/__tests__/build-minisearch.test.ts
```

Expected: FAIL — `Cannot find module '../build-minisearch'`

- [ ] **Step 3: build-minisearch.ts 구현**

`scripts/build-doc-search-index/build-minisearch.ts`:

```ts
import { buildMiniSearchInstance } from '@/lib/doc-search/minisearch-engine';
import type { DocSearchChunk } from '@/lib/doc-search/types';

export function serializeMiniSearchIndex(chunks: DocSearchChunk[]): string {
  const ms = buildMiniSearchInstance(chunks);
  return JSON.stringify(ms);
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
npm run test:run -- scripts/build-doc-search-index/__tests__/build-minisearch.test.ts
```

Expected: `2 passed`

- [ ] **Step 5: index.ts에 MiniSearch 빌드 통합**

`scripts/build-doc-search-index/index.ts`의 `writeDocSearchArtifacts()` 함수에 추가:

```ts
// 기존 import에 추가
import { serializeMiniSearchIndex } from './build-minisearch';

// writeDocSearchArtifacts() 내 for loop 안, 기존 writeFileSync 다음에 추가:
fs.writeFileSync(
  path.join(OUTPUT_ROOT, `${lang}-minisearch.json`),
  serializeMiniSearchIndex(index.chunks),
);
console.log(`Generated MiniSearch index for lang: ${lang}`);
```

- [ ] **Step 6: 전체 테스트 통과 확인**

```bash
npm run test:run
```

Expected: `64 passed` (기존 62 + 신규 2)

- [ ] **Step 7: 커밋**

```bash
git add scripts/build-doc-search-index/build-minisearch.ts scripts/build-doc-search-index/__tests__/build-minisearch.test.ts scripts/build-doc-search-index/index.ts
git commit -m "feat(doc-search): MiniSearch 인덱스 빌드 및 직렬화를 추가합니다"
```

---

## Chunk 4: MiniSearch 인덱스 로드 및 캐시

### Task 4: load-index.ts에 MiniSearch 인덱스 로더 추가

**Files:**
- Modify: `src/lib/doc-search/load-index.ts`

MiniSearch 인덱스는 `MiniSearch.loadJSON()`으로 복원합니다. 기존 `Map<string, ...>` 캐시 패턴을 그대로 따릅니다.

- [ ] **Step 1: load-index.ts 수정**

기존 `pagesCache` 선언 다음에 추가:

```ts
import MiniSearch from 'minisearch';
import type { DocSearchChunk } from '@/lib/doc-search/types';

// 기존 import 아래에 추가
const miniSearchCache = new Map<string, MiniSearch<DocSearchChunk>>();

export function loadMiniSearchIndex(lang = 'ko'): MiniSearch<DocSearchChunk> {
  if (!miniSearchCache.has(lang)) {
    const json = fs.readFileSync(
      path.join(process.cwd(), 'public', '_doc-search', `${lang}-minisearch.json`),
      'utf8',
    );
    miniSearchCache.set(
      lang,
      MiniSearch.loadJSON<DocSearchChunk>(json, {
        fields: ['title', 'headingText', 'content'],
      }),
    );
  }
  return miniSearchCache.get(lang)!;
}
```

- [ ] **Step 2: 전체 테스트 통과 확인**

```bash
npm run test:run
```

Expected: `64 passed`

- [ ] **Step 3: 커밋**

```bash
git add src/lib/doc-search/load-index.ts
git commit -m "feat(doc-search): MiniSearch 인덱스 로드 캐시를 추가합니다"
```

---

## Chunk 5: MCP tool에 searchEngine 파라미터 통합

### Task 5: search_docs tool에 비교 기능 추가

**Files:**
- Modify: `src/lib/doc-search/mcp.ts`
- Modify: `src/lib/doc-search/__tests__/mcp.test.ts`

`searchEngine` 파라미터:
- `custom` (기본값): 기존 커스텀 스코어링
- `minisearch`: MiniSearch BM25+
- `both`: 두 엔진 결과를 나란히 반환

- [ ] **Step 1: mcp.test.ts에 테스트 추가**

`src/lib/doc-search/__tests__/mcp.test.ts`의 `describe('handleMcpJsonRpc')` 블록 안에 추가:

```ts
it('calls search_docs with searchEngine=minisearch', async () => {
  const response = await handleMcpJsonRpc(
    {
      jsonrpc: '2.0',
      id: 10,
      method: 'tools/call',
      params: {
        name: 'search_docs',
        arguments: { query: 'Running Queries', topK: 3, searchEngine: 'minisearch' },
      },
    },
    { artifact, pages },
  );

  expect(response.result).toBeDefined();
  const content = response.result.structuredContent;
  expect(content.engine).toBe('minisearch');
  expect(Array.isArray(content.results)).toBe(true);
});

it('calls search_docs with searchEngine=both', async () => {
  const response = await handleMcpJsonRpc(
    {
      jsonrpc: '2.0',
      id: 11,
      method: 'tools/call',
      params: {
        name: 'search_docs',
        arguments: { query: 'Running Queries', topK: 3, searchEngine: 'both' },
      },
    },
    { artifact, pages },
  );

  expect(response.result).toBeDefined();
  const content = response.result.structuredContent;
  expect(content.custom).toBeDefined();
  expect(content.minisearch).toBeDefined();
  expect(content.custom.engine).toBe('custom');
  expect(content.minisearch.engine).toBe('minisearch');
  expect(typeof content.custom.durationMs).toBe('number');
  expect(typeof content.minisearch.durationMs).toBe('number');
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
npm run test:run -- src/lib/doc-search/__tests__/mcp.test.ts
```

Expected: 2개 실패

- [ ] **Step 3: mcp.ts 수정**

`getTools()` 함수의 `search_docs` 스키마에 파라미터 추가:

```ts
// 기존 manualType 속성 다음에 추가:
searchEngine: {
  type: 'string',
  enum: ['custom', 'minisearch', 'both'],
  default: 'custom',
  description: 'Search engine to use. "both" returns side-by-side comparison for quality evaluation.',
},
```

`handleMcpJsonRpc()`의 `tools/call` → `search_docs` 처리 부분 수정:

```ts
// 기존 import에 추가
import { searchWithMiniSearch, buildMiniSearchInstance } from '@/lib/doc-search/minisearch-engine';
import type { SearchEngine } from '@/lib/doc-search/types';

// search_docs 처리 블록에서 results 계산 전에 추가:
const searchEngine = (args.searchEngine as SearchEngine | undefined) ?? 'custom';
const start = performance.now();

if (searchEngine === 'both') {
  // 커스텀 엔진
  const customStart = performance.now();
  const customResults = searchDocs({ artifact, query, topK: typeof args.topK === 'number' ? args.topK : 5, manualType: args.manualType as ManualType | undefined });
  const customDuration = Math.round((performance.now() - customStart) * 100) / 100;

  // MiniSearch 엔진 (context 주입 또는 실제 인덱스 로드)
  const ms = context?.miniSearchInstance ?? buildMiniSearchInstance(artifact.chunks);
  const msResult = searchWithMiniSearch(ms, { artifact, query, topK: typeof args.topK === 'number' ? args.topK : 5, manualType: args.manualType as ManualType | undefined });

  const comparison = {
    custom: { engine: 'custom', results: customResults, durationMs: customDuration },
    minisearch: msResult,
  };
  return buildSuccess(request.id, {
    content: serializeTextContent(comparison),
    structuredContent: comparison,
  });
}

if (searchEngine === 'minisearch') {
  const ms = context?.miniSearchInstance ?? buildMiniSearchInstance(artifact.chunks);
  const msResult = searchWithMiniSearch(ms, { artifact, query, topK: typeof args.topK === 'number' ? args.topK : 5, manualType: args.manualType as ManualType | undefined });
  return buildSuccess(request.id, {
    content: serializeTextContent(msResult),
    structuredContent: msResult,
  });
}

// 기존 custom 경로는 그대로 유지
const results = searchDocs({ ... });
```

테스트용 `context`에 `miniSearchInstance?: MiniSearch<DocSearchChunk>` 필드를 추가하여 테스트 시 실제 파일 로드 없이 주입 가능하게 합니다.

- [ ] **Step 4: 테스트 통과 확인**

```bash
npm run test:run
```

Expected: `66 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/lib/doc-search/mcp.ts src/lib/doc-search/__tests__/mcp.test.ts
git commit -m "feat(doc-search): search_docs tool에 searchEngine 비교 파라미터를 추가합니다"
```

---

## Chunk 6: 문서 업데이트

### Task 6: DEVELOPMENT.md 및 docs/plans/README.md 업데이트

**Files:**
- Modify: `docs/DEVELOPMENT.md`
- Create: `docs/plans/README.md`

- [ ] **Step 1: docs/plans/README.md 생성**

```markdown
# docs/plans/

구현 계획 문서를 관리합니다.

| 문서 | 설명 |
|------|------|
| [2026-03-17-minisearch-comparison.md](2026-03-17-minisearch-comparison.md) | MiniSearch 기반 검색 비교 구현 계획 |
```

- [ ] **Step 2: DEVELOPMENT.md의 MCP 인덱스 빌드 섹션 업데이트**

수동 빌드 명령 설명에 MiniSearch 인덱스도 함께 생성됨을 명시합니다:

```markdown
> `build-doc-search-index` 실행 시 커스텀 검색 인덱스(`{lang}-index.json`, `{lang}-pages.json`)와
> MiniSearch BM25+ 인덱스(`{lang}-minisearch.json`)가 함께 생성됩니다.
```

- [ ] **Step 3: docs/README.md 업데이트**

기술 문서 테이블에 plans 항목 추가:

```markdown
| [plans/](plans/) | 구현 계획 문서 |
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
npm run test:run
```

Expected: `66 passed`

- [ ] **Step 5: 커밋**

```bash
git add docs/plans/README.md docs/DEVELOPMENT.md docs/README.md
git commit -m "docs: MiniSearch 비교 계획서 디렉토리 및 문서를 추가합니다"
```

---

## 구현 완료 후 검증 방법

### 수동 검증 (MCP Inspector 사용)

```bash
# 1. 인덱스 빌드
npm run build-doc-search-index

# 2. 개발 서버 실행
npm run dev

# 3. MCP Inspector 접속 후 search_docs 호출
# searchEngine: "both" 로 쿼리 → 두 엔진 결과 나란히 확인
```

### 비교 평가 기준

| 기준 | 체크 방법 |
|------|-----------|
| 한국어 검색 정확도 | 형태소 단위 쿼리 (`연결`, `모니터링`) vs 기존 엔진 결과 비교 |
| 긴 자연어 쿼리 | `데이터베이스 연결 설정 방법` 같은 문장형 쿼리 비교 |
| 영어 검색 | `Running Queries`, `Connection Management` 비교 |
| `durationMs` | 응답 속도 비교 (`both` 모드에서 자동 측정) |
| 순위 차이 | 동일 쿼리에서 두 엔진의 top-5 결과 순서 비교 |
