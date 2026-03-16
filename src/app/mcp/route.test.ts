import { describe, expect, it } from 'vitest';
import { NextRequest } from 'next/server';

import { GET, OPTIONS, POST, DELETE } from './route';

function makeRequest(url: string, init?: RequestInit) {
  return new NextRequest(new Request(url, init));
}

describe('/mcp transport', () => {
  it('returns CORS preflight headers for inspector', async () => {
    const response = await OPTIONS(
      makeRequest('http://localhost:3000/mcp', {
        method: 'OPTIONS',
        headers: {
          Origin: 'https://modelcontextprotocol.io',
          'Access-Control-Request-Method': 'POST',
          'Access-Control-Request-Headers': 'content-type,mcp-protocol-version',
        },
      }),
    );

    expect(response.status).toBe(204);
    expect(response.headers.get('access-control-allow-origin')).toBe('https://modelcontextprotocol.io');
    expect(response.headers.get('access-control-allow-methods')).toContain('POST');
    expect(response.headers.get('access-control-allow-headers')).toContain('mcp-protocol-version');
  });

  it('returns SSE stream for GET requests that ask for text/event-stream', async () => {
    const response = await GET(
      makeRequest('http://localhost:3000/mcp', {
        method: 'GET',
        headers: {
          Accept: 'text/event-stream',
          Origin: 'https://modelcontextprotocol.io',
        },
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toContain('text/event-stream');
    expect(response.headers.get('mcp-protocol-version')).toBeTruthy();
  });

  it('returns protocol headers on initialize POST', async () => {
    const response = await POST(
      makeRequest('http://localhost:3000/mcp', {
        method: 'POST',
        headers: {
          Accept: 'application/json, text/event-stream',
          'Content-Type': 'application/json',
          Origin: 'https://modelcontextprotocol.io',
        },
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: 1,
          method: 'initialize',
          params: {
            protocolVersion: '2025-06-18',
            capabilities: {},
            clientInfo: { name: 'mcp-inspector', version: '1.0.0' },
          },
        }),
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toContain('application/json');
    expect(response.headers.get('mcp-protocol-version')).toBe('2025-06-18');
    expect(response.headers.get('access-control-allow-origin')).toBe('https://modelcontextprotocol.io');
  });

  it('accepts notifications with 202', async () => {
    const response = await POST(
      makeRequest('http://localhost:3000/mcp', {
        method: 'POST',
        headers: {
          Accept: 'application/json, text/event-stream',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'notifications/initialized',
          params: {},
        }),
      }),
    );

    expect(response.status).toBe(202);
  });

  it('supports DELETE session cleanup as a no-op', async () => {
    const response = await DELETE(
      makeRequest('http://localhost:3000/mcp', {
        method: 'DELETE',
        headers: {
          Origin: 'https://modelcontextprotocol.io',
        },
      }),
    );

    expect(response.status).toBe(204);
  });
});
