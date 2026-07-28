import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  expandContentRouteRedirects,
  loadActiveContentRouteRedirects,
} from './content-route-redirects';

function writeRegistry(contents: string): string {
  const directory = mkdtempSync(path.join(tmpdir(), 'content-redirects-'));
  const registryPath = path.join(directory, 'redirects.yaml');
  writeFileSync(registryPath, contents, 'utf8');
  return registryPath;
}

describe('content route redirects', () => {
  it('loads only active redirects and expands locale routes', () => {
    const filePath = writeRegistry(`
- source: /support/active-old
  destination: /support/active-new
  created_on: '2026-07-28'
  expires_on: '2026-09-22'
- source: /support/expired-old
  destination: /support/expired-new
  created_on: '2026-05-01'
  expires_on: '2026-06-26'
`);

    const active = loadActiveContentRouteRedirects({
      filePath,
      currentDate: new Date('2026-07-28T12:00:00.000Z'),
    });

    expect(active).toEqual([{
      source: '/support/active-old',
      destination: '/support/active-new',
      created_on: '2026-07-28',
      expires_on: '2026-09-22',
    }]);
    expect(expandContentRouteRedirects(active)).toEqual([
      {
        source: '/:locale(ko|en|ja)/support/active-old',
        destination: '/:locale/support/active-new',
        permanent: false,
      },
      {
        source: '/support/active-old',
        destination: '/support/active-new',
        permanent: false,
      },
    ]);
  });

  it('treats expires_on as the first inactive date', () => {
    const filePath = writeRegistry(`
- source: /old
  destination: /new
  created_on: '2026-07-28'
  expires_on: '2026-09-22'
`);

    expect(loadActiveContentRouteRedirects({
      filePath,
      currentDate: new Date('2026-09-22T00:00:00.000Z'),
    })).toEqual([]);
  });

  it('rejects duplicate sources and invalid lifecycle metadata', () => {
    const filePath = writeRegistry(`
- source: /old
  destination: /new
  created_on: '2026-07-28'
  expires_on: '2026-07-28'
- source: /old
  destination: /another
  created_on: '2026-07-28'
  expires_on: '2026-09-22'
`);

    expect(() => loadActiveContentRouteRedirects({
      filePath,
      currentDate: new Date('2026-07-28T00:00:00.000Z'),
    })).toThrow('expires_on must be later than created_on');
  });
});
