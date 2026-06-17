import { describe, expect, it } from 'vitest';

import {
  DOCS_SPOTLIGHT_STORAGE_KEY,
  parseDocsSpotlightVisibilityRecords,
  readDocsSpotlightVisibilityState,
  writeDocsSpotlightVisibilityRecord,
} from './storage';

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();

  return {
    clear: () => values.clear(),
    getItem: key => values.get(key) ?? null,
    key: index => Array.from(values.keys())[index] ?? null,
    get length() {
      return values.size;
    },
    removeItem: key => values.delete(key),
    setItem: (key, value) => values.set(key, String(value)),
  } as Storage;
}

describe('docs spotlight storage', () => {
  it('parses visibility records and marks expired records', () => {
    expect(
      parseDocsSpotlightVisibilityRecords(
        JSON.stringify({
          active: {
            disposition: 'viewed',
            updatedAt: '2099-06-12T00:00:00.000Z',
            expiresAt: '2099-07-12T00:00:00.000Z',
          },
          expired: {
            disposition: 'dismissed',
            updatedAt: '2020-06-12T00:00:00.000Z',
            expiresAt: '2020-07-12T00:00:00.000Z',
          },
        }),
        new Date('2026-06-12T00:00:00.000Z'),
      ),
    ).toEqual([
      {
        disposition: 'viewed',
        expiresAt: '2099-07-12T00:00:00.000Z',
        id: 'active',
        isExpired: false,
        updatedAt: '2099-06-12T00:00:00.000Z',
      },
      {
        disposition: 'dismissed',
        expiresAt: '2020-07-12T00:00:00.000Z',
        id: 'expired',
        isExpired: true,
        updatedAt: '2020-06-12T00:00:00.000Z',
      },
    ]);
  });

  it('recovers from corrupt payloads and prunes expired records', () => {
    const storage = createMemoryStorage();

    storage.setItem(
      DOCS_SPOTLIGHT_STORAGE_KEY,
      JSON.stringify({
        active: {
          disposition: 'viewed',
          updatedAt: '2099-06-12T00:00:00.000Z',
          expiresAt: '2099-07-12T00:00:00.000Z',
        },
        expired: {
          disposition: 'dismissed',
          updatedAt: '2020-06-12T00:00:00.000Z',
          expiresAt: '2020-07-12T00:00:00.000Z',
        },
      }),
    );

    expect(readDocsSpotlightVisibilityState(storage, new Date('2026-06-12T00:00:00.000Z'))).toEqual({
      active: {
        disposition: 'viewed',
        expiresAt: '2099-07-12T00:00:00.000Z',
        updatedAt: '2099-06-12T00:00:00.000Z',
      },
    });
    expect(storage.getItem(DOCS_SPOTLIGHT_STORAGE_KEY)).toContain('active');
    expect(storage.getItem(DOCS_SPOTLIGHT_STORAGE_KEY)).not.toContain('expired');

    storage.setItem(DOCS_SPOTLIGHT_STORAGE_KEY, 'not-json');
    expect(readDocsSpotlightVisibilityState(storage)).toEqual({});
  });

  it('writes a viewed or dismissed record with a 30-day TTL', () => {
    const storage = createMemoryStorage();

    expect(
      writeDocsSpotlightVisibilityRecord(
        storage,
        'iso-42001-certification',
        'dismissed',
        new Date('2026-06-12T00:00:00.000Z'),
      ),
    ).toBe(true);

    expect(JSON.parse(storage.getItem(DOCS_SPOTLIGHT_STORAGE_KEY) ?? '{}')).toEqual({
      'iso-42001-certification': {
        disposition: 'dismissed',
        updatedAt: '2026-06-12T00:00:00.000Z',
        expiresAt: '2026-07-12T00:00:00.000Z',
      },
    });
  });
});
