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
    const result = searchWithMiniSearch(ms, { query: '쿼리', topK: 5 });
    expect(result.engine).toBe('minisearch');
    expect(result.durationMs).toBeGreaterThanOrEqual(0);
    expect(result.results.length).toBeGreaterThan(0);
  });

  it('respects topK limit', () => {
    const ms = buildMiniSearchInstance(sampleChunks);
    const result = searchWithMiniSearch(ms, { query: '관리', topK: 1 });
    expect(result.results.length).toBeLessThanOrEqual(1);
  });

  it('applies manualType filter', () => {
    const ms = buildMiniSearchInstance(sampleChunks);
    const result = searchWithMiniSearch(ms, {
      query: '연결',
      topK: 5,
      manualType: 'user-manual',
    });
    expect(result.results.length).toBe(0);
  });
});
