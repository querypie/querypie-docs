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

type DocWithHeadingText = DocSearchChunk & { headingText: string };

// loadJSON 시 동일한 옵션을 전달하기 위해 export합니다.
export const MINISEARCH_LOAD_OPTIONS = {
  fields: ['title', 'headingText', 'content'] as string[],
  tokenize: segmentText,
  processTerm: (term: string) => term.toLowerCase(),
  searchOptions: {
    boost: { title: 3, headingText: 2, content: 1 },
    fuzzy: 0.1,
    prefix: true,
  },
};

export function buildMiniSearchInstance(chunks: DocSearchChunk[]): MiniSearch<DocSearchChunk> {
  const ms = new MiniSearch<DocWithHeadingText>({
    idField: 'id',
    storeFields: ['id', 'pagePath', 'url', 'title', 'description', 'headingPath', 'content', 'excerpt', 'metadata'],
    ...MINISEARCH_LOAD_OPTIONS,
  });

  // headingPath 배열을 단일 문자열 필드로 변환하여 인덱싱
  const docs = chunks.map(chunk => ({
    ...chunk,
    headingText: chunk.headingPath.join(' '),
  }));

  ms.addAll(docs);
  return ms as unknown as MiniSearch<DocSearchChunk>;
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
