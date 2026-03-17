import { describe, expect, it } from 'vitest';

import type { DocSearchPagesArtifact } from '@/lib/doc-search/types';
import { handleMcpJsonRpc, MCP_PROTOCOL_VERSION, SUPPORTED_LANGS } from '@/lib/doc-search/mcp';
import { buildMiniSearchInstance } from '@/lib/doc-search/minisearch-engine';

const sampleChunks = [
  {
    id: '1',
    pagePath: 'administrator-manual/databases/monitoring',
    url: '/ko/administrator-manual/databases/monitoring',
    title: 'Monitoring',
    description: '모니터링 기능 설명',
    headingPath: ['Monitoring', 'Overview'],
    content: 'Running Queries 기능과 Proxy Management를 통해 상태를 확인하고 강제 중지할 수 있습니다.',
    excerpt: 'Running Queries 기능과 Proxy Management를 통해 상태를 확인하고 강제 중지할 수 있습니다.',
    metadata: {
      lang: 'ko',
      manualType: 'administrator-manual' as const,
      productArea: 'databases',
      versionHints: ['10.3.0'],
      isUnreleased: false,
    },
  },
];

const pages: DocSearchPagesArtifact = {
  version: 1,
  generatedAt: '2026-03-16T00:00:00.000Z',
  lang: 'ko',
  pages: {
    'administrator-manual/databases/monitoring': {
      pagePath: 'administrator-manual/databases/monitoring',
      url: '/ko/administrator-manual/databases/monitoring',
      title: 'Monitoring',
      description: '모니터링 기능 설명',
      content: '# Monitoring\n\n### Overview\n\nRunning Queries 기능 설명',
      tableOfContents: ['Monitoring', 'Overview'],
      metadata: {
        lang: 'ko',
        manualType: 'administrator-manual',
        productArea: 'databases',
        versionHints: ['10.3.0'],
        isUnreleased: false,
      },
    },
  },
};

describe('handleMcpJsonRpc', () => {
  it('responds to initialize', async () => {
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
          protocolVersion: MCP_PROTOCOL_VERSION,
          capabilities: {},
          clientInfo: { name: 'test-client', version: '1.0.0' },
        },
      },
      { pages, miniSearchInstance },
    );

    expect((response.result as Record<string, unknown>).protocolVersion).toBe(MCP_PROTOCOL_VERSION);
    expect((response.result as Record<string, unknown>).capabilities).toEqual({ tools: {} });
  });

  it('lists search tools', async () => {
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      { jsonrpc: '2.0', id: 2, method: 'tools/list' },
      { pages, miniSearchInstance },
    );

    expect(((response.result as Record<string, unknown>).tools as { name: string }[]).map(tool => tool.name)).toEqual(['search_docs', 'get_doc_page']);
  });

  it('calls search_docs and returns structured content', async () => {
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 3,
        method: 'tools/call',
        params: { name: 'search_docs', arguments: { query: 'Running Queries', topK: 3 } },
      },
      { pages, miniSearchInstance },
    );

    const content = response.result as Record<string, unknown>;
    expect(content.structuredContent).toBeDefined();
    const structured = content.structuredContent as Record<string, unknown>;
    expect(structured.engine).toBe('minisearch');
    expect((content.content as { type: string }[])[0].type).toBe('text');
  });

  it('calls get_doc_page and returns full page content', async () => {
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 4,
        method: 'tools/call',
        params: { name: 'get_doc_page', arguments: { pagePath: 'administrator-manual/databases/monitoring' } },
      },
      { pages, miniSearchInstance },
    );

    const structured = (response.result as Record<string, unknown>).structuredContent as Record<string, unknown>;
    const page = structured.page as Record<string, unknown>;
    expect(page.title).toBe('Monitoring');
    expect(page.tableOfContents).toEqual(['Monitoring', 'Overview']);
  });

  it('returns json-rpc error for unknown tools', async () => {
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 5,
        method: 'tools/call',
        params: { name: 'nope', arguments: {} },
      },
      { pages, miniSearchInstance },
    );

    expect(response.error?.code).toBe(-32601);
  });
});

// ---------------------------------------------------------------------------
// lang 입력 검증 (#932 버그 수정)
// ---------------------------------------------------------------------------

describe('handleMcpJsonRpc — lang 입력 검증', () => {
  /**
   * 수정 전 동작 (버그):
   *   lang: 'fr' 로 search_docs 를 호출하면
   *   load-index.ts 에서 fr-minisearch.json 파일을 찾지 못해
   *   ENOENT 예외가 throw 되고, route.ts 에서 잡히지 않아 HTTP 500이 됩니다.
   *   JSON-RPC 규약상 잘못된 파라미터는 -32602 Invalid params 로 처리해야 합니다.
   *
   * 수정 후 동작:
   *   tools/call 진입 시 lang 을 SUPPORTED_LANGS(['ko', 'en', 'ja'])로 검증하여
   *   지원하지 않는 값이면 -32602 에러를 즉시 반환합니다.
   *   파일 I/O 에 도달하지 않으므로 ENOENT 예외가 발생하지 않습니다.
   */
  it('search_docs 에서 지원하지 않는 lang은 -32602 에러를 반환합니다', async () => {
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 10,
        method: 'tools/call',
        params: { name: 'search_docs', arguments: { query: '설치', lang: 'fr' } },
      },
      { pages, miniSearchInstance },
    );

    // JSON-RPC 에러 응답 구조
    expect(response.jsonrpc).toBe('2.0');
    expect(response.id).toBe(10);
    expect(response.error).toBeDefined();
    expect(response.result).toBeUndefined();

    // -32602 Invalid params (파일 I/O 예외가 아님)
    expect(response.error?.code).toBe(-32602);
    expect(response.error?.message).toContain('fr');
    expect(response.error?.message).toContain('ko, en, ja');
  });

  it('get_doc_page 에서 지원하지 않는 lang은 -32602 에러를 반환합니다', async () => {
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 11,
        method: 'tools/call',
        params: {
          name: 'get_doc_page',
          arguments: { pagePath: 'administrator-manual/databases/monitoring', lang: 'zh' },
        },
      },
      { pages, miniSearchInstance },
    );

    expect(response.error?.code).toBe(-32602);
    expect(response.error?.message).toContain('zh');
  });

  it('lang 을 생략하면 기본값 en 으로 정상 동작합니다', async () => {
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 12,
        method: 'tools/call',
        params: { name: 'search_docs', arguments: { query: 'Running Queries' } },
      },
      { pages, miniSearchInstance },
    );

    // 에러 없이 정상 응답 (context 주입으로 파일 로드 없이 동작)
    expect(response.error).toBeUndefined();
    expect(response.result).toBeDefined();
  });

  it.each(SUPPORTED_LANGS)('지원 lang "%s" 는 에러 없이 통과합니다', async (lang) => {
    // context 에 인스턴스를 주입해 파일 로드 없이 lang 검증만 테스트합니다
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 20,
        method: 'tools/call',
        params: { name: 'search_docs', arguments: { query: 'test', lang } },
      },
      { pages, miniSearchInstance },
    );

    // lang 검증은 통과하므로 에러 없이 result 가 반환됩니다
    expect(response.error).toBeUndefined();
    expect(response.result).toBeDefined();
  });

  it('빈 문자열 lang은 기본값 en 으로 처리됩니다', async () => {
    // String('' || 'en') === 'en' 이므로 검증 통과
    const miniSearchInstance = buildMiniSearchInstance(sampleChunks);
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 13,
        method: 'tools/call',
        params: { name: 'search_docs', arguments: { query: '검색', lang: '' } },
      },
      { pages, miniSearchInstance },
    );

    expect(response.error).toBeUndefined();
    expect(response.result).toBeDefined();
  });
});
