export const DOCS_SPOTLIGHT_STORAGE_KEY = 'querypie:docs:spotlight:v1';
export const DOCS_SPOTLIGHT_VISIBILITY_TTL_MS = 30 * 24 * 60 * 60 * 1000;

export type DocsSpotlightDisposition = 'viewed' | 'dismissed';

export type DocsSpotlightVisibilityRecord = {
  disposition: DocsSpotlightDisposition;
  updatedAt: string;
  expiresAt: string;
};

export type DocsSpotlightVisibilityState = Record<string, DocsSpotlightVisibilityRecord>;

export type ParsedDocsSpotlightVisibilityRecord = DocsSpotlightVisibilityRecord & {
  id: string;
  isExpired: boolean;
};

const validDispositions = new Set<DocsSpotlightDisposition>(['viewed', 'dismissed']);

export function getDocsSpotlightBrowserLocalStorage() {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function assertTimestamp(value: unknown, fieldName: string, recordId: string) {
  if (typeof value !== 'string' || !Number.isFinite(Date.parse(value))) {
    throw new Error(`Invalid ${fieldName} timestamp for ${recordId}`);
  }

  return value;
}

function normalizeVisibilityRecord(
  id: string,
  candidate: unknown,
  now: Date,
): ParsedDocsSpotlightVisibilityRecord {
  if (!isObject(candidate)) {
    throw new Error(`Expected docs spotlight visibility record for ${id} to be an object`);
  }

  const disposition = candidate.disposition;

  if (typeof disposition !== 'string' || !validDispositions.has(disposition as DocsSpotlightDisposition)) {
    throw new Error(`Invalid disposition for ${id}`);
  }

  const updatedAt = assertTimestamp(candidate.updatedAt, 'updatedAt', id);
  const expiresAt = assertTimestamp(candidate.expiresAt, 'expiresAt', id);

  return {
    disposition: disposition as DocsSpotlightDisposition,
    expiresAt,
    id,
    isExpired: Date.parse(expiresAt) <= now.getTime(),
    updatedAt,
  };
}

function persistVisibilityState(storage: Storage, state: DocsSpotlightVisibilityState) {
  if (Object.keys(state).length === 0) {
    storage.removeItem(DOCS_SPOTLIGHT_STORAGE_KEY);
    return;
  }

  storage.setItem(DOCS_SPOTLIGHT_STORAGE_KEY, JSON.stringify(state));
}

export function parseDocsSpotlightVisibilityRecords(
  rawValue: string,
  now: Date = new Date(),
): ParsedDocsSpotlightVisibilityRecord[] {
  const parsedValue: unknown = JSON.parse(rawValue);

  if (!isObject(parsedValue)) {
    throw new Error('Expected docs spotlight visibility state to be an object map');
  }

  return Object.entries(parsedValue)
    .map(([id, candidate]) => normalizeVisibilityRecord(id, candidate, now))
    .sort((left, right) => left.id.localeCompare(right.id));
}

export function readDocsSpotlightVisibilityState(
  storage: Storage,
  now: Date = new Date(),
): DocsSpotlightVisibilityState {
  try {
    const rawValue = storage.getItem(DOCS_SPOTLIGHT_STORAGE_KEY);

    if (!rawValue) {
      return {};
    }

    const parsedValue: unknown = JSON.parse(rawValue);

    if (!isObject(parsedValue)) {
      try {
        storage.removeItem(DOCS_SPOTLIGHT_STORAGE_KEY);
      } catch {
        // Best-effort cleanup; rendering should continue from an empty state.
      }

      return {};
    }

    const nextState: DocsSpotlightVisibilityState = {};
    let shouldPersistPrunedState = false;

    for (const [id, candidate] of Object.entries(parsedValue)) {
      try {
        const record = normalizeVisibilityRecord(id, candidate, now);

        if (record.isExpired) {
          shouldPersistPrunedState = true;
          continue;
        }

        nextState[id] = {
          disposition: record.disposition,
          expiresAt: record.expiresAt,
          updatedAt: record.updatedAt,
        };
      } catch {
        shouldPersistPrunedState = true;
      }
    }

    if (shouldPersistPrunedState) {
      try {
        persistVisibilityState(storage, nextState);
      } catch {
        // Pruning failure must not block visibility decisions.
      }
    }

    return nextState;
  } catch {
    return {};
  }
}

export function writeDocsSpotlightVisibilityRecord(
  storage: Storage,
  id: string,
  disposition: DocsSpotlightDisposition,
  now: Date = new Date(),
) {
  try {
    const updatedAt = now.toISOString();
    const expiresAt = new Date(now.getTime() + DOCS_SPOTLIGHT_VISIBILITY_TTL_MS).toISOString();
    const nextState = {
      ...readDocsSpotlightVisibilityState(storage, now),
      [id]: {
        disposition,
        expiresAt,
        updatedAt,
      },
    };

    storage.setItem(DOCS_SPOTLIGHT_STORAGE_KEY, JSON.stringify(nextState));

    return true;
  } catch {
    return false;
  }
}
