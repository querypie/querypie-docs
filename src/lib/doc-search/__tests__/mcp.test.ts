import { describe, expect, it } from 'vitest';

import type { DocSearchArtifact, DocSearchPagesArtifact } from '@/lib/doc-search/types';
import { handleMcpJsonRpc, MCP_PROTOCOL_VERSION } from '@/lib/doc-search/mcp';

const artifact: DocSearchArtifact = {
  version: 1,
  generatedAt: '2026-03-16T00:00:00.000Z',
  lang: 'ko',
  chunks: [
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
        manualType: 'administrator-manual',
        productArea: 'databases',
        versionHints: ['10.3.0'],
        isUnreleased: false,
      },
    },
  ],
};

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
      { artifact, pages },
    );

    expect(response.result.protocolVersion).toBe(MCP_PROTOCOL_VERSION);
    expect(response.result.capabilities.tools).toEqual({});
  });

  it('lists search tools', async () => {
    const response = await handleMcpJsonRpc(
      { jsonrpc: '2.0', id: 2, method: 'tools/list' },
      { artifact, pages },
    );

    expect(response.result.tools.map((tool: { name: string }) => tool.name)).toEqual(['search_docs', 'get_doc_page']);
  });

  it('calls search_docs and returns structured content', async () => {
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 3,
        method: 'tools/call',
        params: { name: 'search_docs', arguments: { query: 'Running Queries', topK: 3 } },
      },
      { artifact, pages },
    );

    expect(response.result.structuredContent.results[0].pagePath).toBe('administrator-manual/databases/monitoring');
    expect(response.result.content[0].type).toBe('text');
  });

  it('calls get_doc_page and returns full page content', async () => {
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 4,
        method: 'tools/call',
        params: { name: 'get_doc_page', arguments: { pagePath: 'administrator-manual/databases/monitoring' } },
      },
      { artifact, pages },
    );

    expect(response.result.structuredContent.page.title).toBe('Monitoring');
    expect(response.result.structuredContent.page.tableOfContents).toEqual(['Monitoring', 'Overview']);
  });

  it('returns json-rpc error for unknown tools', async () => {
    const response = await handleMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 5,
        method: 'tools/call',
        params: { name: 'nope', arguments: {} },
      },
      { artifact, pages },
    );

    expect(response.error.code).toBe(-32601);
  });
});
