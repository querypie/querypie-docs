import { describe, expect, it } from 'vitest';
import MiniSearch from 'minisearch';
import { serializeMiniSearchIndex } from '../build-minisearch';
import { MINISEARCH_LOAD_OPTIONS } from '@/lib/doc-search/minisearch-engine';
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
    const ms = MiniSearch.loadJSON<DocSearchChunk>(json, MINISEARCH_LOAD_OPTIONS);
    const results = ms.search('쿼리파이');
    expect(results.length).toBeGreaterThan(0);
  });
});
