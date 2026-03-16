import type MiniSearch from 'minisearch';

import type { DocSearchArtifact, DocSearchChunk, DocSearchPagesArtifact, ManualType, SearchEngine } from '@/lib/doc-search/types';
import { getDocPage } from '@/lib/doc-search/get-page';
import { loadDocSearchArtifact, loadMiniSearchIndex } from '@/lib/doc-search/load-index';
import { searchWithMiniSearch } from '@/lib/doc-search/minisearch-engine';
import { searchDocs } from '@/lib/doc-search/search';

// Versions listed in descending order (newest first).
// Default is set to the latest supported version per MCP spec:
// the server should advertise the highest version it supports.
export const MCP_PROTOCOL_VERSION = '2025-11-25';
export const SUPPORTED_PROTOCOL_VERSIONS = ['2025-11-25', '2025-06-18', '2025-03-26'] as const;

interface JsonRpcRequest {
  jsonrpc: '2.0';
  id?: string | number | null;
  method: string;
  params?: Record<string, unknown>;
}

interface JsonRpcResponse {
  jsonrpc: '2.0';
  id: string | number | null;
  result?: unknown;
  error?: {
    code: number;
    message: string;
  };
}

function buildSuccess(id: JsonRpcRequest['id'], result: unknown): JsonRpcResponse {
  return { jsonrpc: '2.0', id: id ?? null, result };
}

function buildError(id: JsonRpcRequest['id'], code: number, message: string): JsonRpcResponse {
  return { jsonrpc: '2.0', id: id ?? null, error: { code, message } };
}

function getTools() {
  return [
    {
      name: 'search_docs',
      description: 'Search Korean QueryPie docs and return high-signal chunks with citation URLs.',
      inputSchema: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Natural language or keyword query.' },
          lang: { type: 'string', enum: ['ko', 'en', 'ja'], default: 'ko' },
          topK: { type: 'integer', minimum: 1, maximum: 10, default: 5 },
          manualType: {
            type: 'string',
            enum: ['overview', 'user-manual', 'administrator-manual', 'installation', 'release-notes', 'api-reference', 'support', 'unreleased'],
          },
          searchEngine: {
            type: 'string',
            enum: ['custom', 'minisearch', 'both'],
            default: 'custom',
            description: 'Search engine to use. "both" returns side-by-side comparison for quality evaluation.',
          },
        },
        required: ['query'],
        additionalProperties: false,
      },
    },
    {
      name: 'get_doc_page',
      description: 'Return normalized full-page content for a QueryPie docs page path.',
      inputSchema: {
        type: 'object',
        properties: {
          pagePath: { type: 'string', description: 'Page path without locale prefix.' },
          lang: { type: 'string', enum: ['ko', 'en', 'ja'], default: 'ko' },
        },
        required: ['pagePath'],
        additionalProperties: false,
      },
    },
  ];
}

function serializeTextContent(payload: unknown) {
  return [
    {
      type: 'text',
      text: JSON.stringify(payload, null, 2),
    },
  ];
}

export async function handleMcpJsonRpc(
  request: JsonRpcRequest,
  context?: { artifact?: DocSearchArtifact; pages?: DocSearchPagesArtifact; miniSearchInstance?: MiniSearch<DocSearchChunk> },
): Promise<JsonRpcResponse> {
  if (request.jsonrpc !== '2.0') {
    return buildError(request.id, -32600, 'Invalid JSON-RPC version');
  }

  switch (request.method) {
    case 'initialize':
      {
        const requestedProtocolVersion = String(request.params?.protocolVersion || MCP_PROTOCOL_VERSION);
        if (!SUPPORTED_PROTOCOL_VERSIONS.includes(requestedProtocolVersion as (typeof SUPPORTED_PROTOCOL_VERSIONS)[number])) {
          return buildError(request.id, -32602, `Unsupported protocol version: ${requestedProtocolVersion}`);
        }

      return buildSuccess(request.id, {
        protocolVersion: requestedProtocolVersion,
        capabilities: {
          tools: {},
        },
        serverInfo: {
          name: 'querypie-docs-mcp',
          version: '0.1.0',
        },
      });
      }
    case 'notifications/initialized':
    case 'ping':
      return buildSuccess(request.id, {});
    case 'tools/list':
      return buildSuccess(request.id, {
        tools: getTools(),
      });
    case 'tools/call': {
      const toolName = String(request.params?.name || '');
      const args = (request.params?.arguments as Record<string, unknown> | undefined) ?? {};
      const lang = String(args.lang || 'ko');
      const artifact = context?.artifact ?? loadDocSearchArtifact(lang);

      if (toolName === 'search_docs') {
        const query = String(args.query || '').trim();
        if (!query) {
          return buildError(request.id, -32602, 'search_docs requires a non-empty query');
        }

        const searchEngine = (args.searchEngine as SearchEngine | undefined) ?? 'custom';
        const topK = typeof args.topK === 'number' ? args.topK : 5;
        const manualType = args.manualType as ManualType | undefined;

        if (searchEngine === 'both') {
          const customStart = performance.now();
          const customResults = searchDocs({ artifact, query, topK, manualType });
          const customDuration = Math.round((performance.now() - customStart) * 100) / 100;

          // instance 취득(캐시 미스 시 파일 로드 포함)부터 검색 완료까지 전체 시간을 측정합니다.
          const msStart = performance.now();
          const ms = context?.miniSearchInstance ?? loadMiniSearchIndex(lang);
          const msResult = searchWithMiniSearch(ms, { artifact, query, topK, manualType });
          msResult.durationMs = Math.round((performance.now() - msStart) * 100) / 100;

          const comparison = {
            custom: { engine: 'custom' as const, results: customResults, durationMs: customDuration },
            minisearch: msResult,
          };
          return buildSuccess(request.id, {
            content: serializeTextContent(comparison),
            structuredContent: comparison,
          });
        }

        if (searchEngine === 'minisearch') {
          // instance 취득(캐시 미스 시 파일 로드 포함)부터 검색 완료까지 전체 시간을 측정합니다.
          const msStart = performance.now();
          const ms = context?.miniSearchInstance ?? loadMiniSearchIndex(lang);
          const msResult = searchWithMiniSearch(ms, { artifact, query, topK, manualType });
          msResult.durationMs = Math.round((performance.now() - msStart) * 100) / 100;
          return buildSuccess(request.id, {
            content: serializeTextContent(msResult),
            structuredContent: msResult,
          });
        }

        const results = searchDocs({ artifact, query, topK, manualType });

        return buildSuccess(request.id, {
          content: serializeTextContent({ results }),
          structuredContent: { results },
        });
      }

      if (toolName === 'get_doc_page') {
        const pagePath = String(args.pagePath || '').trim();
        if (!pagePath) {
          return buildError(request.id, -32602, 'get_doc_page requires pagePath');
        }

        const page = context?.pages?.pages[pagePath] ?? getDocPage(pagePath, String(args.lang || 'ko'));
        if (!page) {
          return buildError(request.id, -32602, `Unknown pagePath: ${pagePath}`);
        }

        return buildSuccess(request.id, {
          content: serializeTextContent({ page }),
          structuredContent: { page },
        });
      }

      return buildError(request.id, -32601, `Unknown tool: ${toolName}`);
    }
    default:
      return buildError(request.id, -32601, `Unknown method: ${request.method}`);
  }
}
