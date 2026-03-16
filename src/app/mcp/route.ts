import { randomUUID } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';

import { handleMcpJsonRpc, MCP_PROTOCOL_VERSION, SUPPORTED_PROTOCOL_VERSIONS } from '@/lib/doc-search/mcp';

const MAX_REQUESTS_PER_MINUTE = 120;
// TODO(#922): This in-memory store is ineffective in serverless environments — each cold start
// resets the counter and multiple instances each have their own store. Expired entries also
// accumulate indefinitely. Replace with a distributed KV store (e.g. Upstash) when stricter
// rate limiting is required. https://github.com/querypie/querypie-docs/issues/922
const rateLimitStore = new Map<string, { count: number; resetAt: number }>();
const ALLOWED_CORS_HEADERS = [
  'content-type',
  'accept',
  'mcp-protocol-version',
  'mcp-session-id',
  'last-event-id',
];

function getClientKey(request: NextRequest): string {
  const forwardedFor = request.headers.get('x-forwarded-for');
  // NOTE(#922): Clients without x-forwarded-for share the 'unknown' bucket, which can cause
  // unrelated clients to block each other. Acceptable until a distributed rate limiter is in place.
  // https://github.com/querypie/querypie-docs/issues/922
  return forwardedFor?.split(',')[0]?.trim() || 'unknown';
}

function isRateLimited(clientKey: string): boolean {
  const now = Date.now();
  const existing = rateLimitStore.get(clientKey);
  if (!existing || existing.resetAt <= now) {
    rateLimitStore.set(clientKey, { count: 1, resetAt: now + 60_000 });
    return false;
  }

  existing.count += 1;
  rateLimitStore.set(clientKey, existing);
  return existing.count > MAX_REQUESTS_PER_MINUTE;
}

function isAllowedOrigin(origin: string, requestHost: string): boolean {
  try {
    const originUrl = new URL(origin);
    const hostname = originUrl.hostname;
    const isLocalHost = ['localhost', '127.0.0.1'].includes(requestHost);

    if (isLocalHost) {
      return [
        'localhost',
        '127.0.0.1',
        'modelcontextprotocol.io',
        'inspector.modelcontextprotocol.io',
      ].includes(hostname);
    }

    if (hostname === requestHost || hostname === 'docs.querypie.com' || hostname === 'docs-staging.querypie.io') {
      return true;
    }

    // /mcp is a public API — all HTTPS origins are intentionally allowed so that any
    // MCP client or web application can call this endpoint without CORS restrictions.
    return originUrl.protocol === 'https:';
  } catch {
    return false;
  }
}

function buildCorsHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  const origin = request.headers.get('origin');

  if (origin && isAllowedOrigin(origin, request.nextUrl.hostname)) {
    headers.set('Access-Control-Allow-Origin', origin);
    headers.set('Vary', 'Origin');
  }

  headers.set('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  headers.set('Access-Control-Allow-Headers', ALLOWED_CORS_HEADERS.join(', '));
  headers.set('Access-Control-Expose-Headers', 'MCP-Protocol-Version, MCP-Session-Id');
  headers.set('Access-Control-Max-Age', '86400');
  return headers;
}

function forbiddenOriginResponse(request: NextRequest): NextResponse | null {
  const origin = request.headers.get('origin');
  if (!origin) {
    return null;
  }

  if (!isAllowedOrigin(origin, request.nextUrl.hostname)) {
    return NextResponse.json({ error: 'Forbidden origin' }, { status: 403 });
  }

  return null;
}

function getProtocolVersion(request: NextRequest, bodyVersion?: unknown): string {
  const requestedVersion = String(bodyVersion || request.headers.get('mcp-protocol-version') || MCP_PROTOCOL_VERSION);
  if (SUPPORTED_PROTOCOL_VERSIONS.includes(requestedVersion as (typeof SUPPORTED_PROTOCOL_VERSIONS)[number])) {
    return requestedVersion;
  }
  return MCP_PROTOCOL_VERSION;
}

function withCommonHeaders(response: NextResponse, request: NextRequest, protocolVersion: string): NextResponse {
  const corsHeaders = buildCorsHeaders(request);
  corsHeaders.forEach((value, key) => response.headers.set(key, value));
  response.headers.set('MCP-Protocol-Version', protocolVersion);
  response.headers.set('Allow', 'GET, POST, DELETE, OPTIONS');
  return response;
}

function createSseResponse(request: NextRequest, protocolVersion: string): NextResponse {
  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      controller.enqueue(encoder.encode(`id: ${randomUUID()}\n`));
      controller.enqueue(encoder.encode('event: message\n'));
      controller.enqueue(encoder.encode('data: {}\n\n'));
      controller.close();
    },
  });

  const response = new NextResponse(stream, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
    },
  });

  return withCommonHeaders(response, request, protocolVersion);
}

export async function OPTIONS(request: NextRequest) {
  const forbidden = forbiddenOriginResponse(request);
  if (forbidden) {
    return forbidden;
  }

  return withCommonHeaders(new NextResponse(null, { status: 204 }), request, getProtocolVersion(request));
}

export async function GET(request: NextRequest) {
  const forbidden = forbiddenOriginResponse(request);
  if (forbidden) {
    return forbidden;
  }

  const protocolVersion = getProtocolVersion(request);
  const accept = request.headers.get('accept') || '';
  if (accept.includes('text/event-stream')) {
    return createSseResponse(request, protocolVersion);
  }

  return withCommonHeaders(
    NextResponse.json(
      {
        name: 'querypie-docs-mcp',
        transport: 'streamable-http',
        methods: ['GET', 'POST', 'DELETE', 'OPTIONS'],
        tools: ['search_docs', 'get_doc_page'],
      },
      { status: 200 },
    ),
    request,
    protocolVersion,
  );
}

export async function DELETE(request: NextRequest) {
  const forbidden = forbiddenOriginResponse(request);
  if (forbidden) {
    return forbidden;
  }

  return withCommonHeaders(new NextResponse(null, { status: 204 }), request, getProtocolVersion(request));
}

export async function POST(request: NextRequest) {
  const forbidden = forbiddenOriginResponse(request);
  if (forbidden) {
    return forbidden;
  }

  const clientKey = getClientKey(request);
  if (isRateLimited(clientKey)) {
    return withCommonHeaders(NextResponse.json({ error: 'Too many requests' }, { status: 429 }), request, getProtocolVersion(request));
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return withCommonHeaders(NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 }), request, getProtocolVersion(request));
  }

  const protocolVersion = getProtocolVersion(request, body.params && typeof body.params === 'object' ? (body.params as Record<string, unknown>).protocolVersion : undefined);

  if (body.id === undefined || body.id === null) {
    await handleMcpJsonRpc(body as never);
    return withCommonHeaders(new NextResponse(null, { status: 202 }), request, protocolVersion);
  }

  const responseBody = await handleMcpJsonRpc(body as never);
  return withCommonHeaders(NextResponse.json(responseBody, { status: 200 }), request, protocolVersion);
}
