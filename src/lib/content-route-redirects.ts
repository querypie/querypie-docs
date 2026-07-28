import { readFileSync } from 'node:fs';
import path from 'node:path';
import { load } from 'js-yaml';

export type ContentRouteRedirect = {
  source: string;
  destination: string;
  created_on: string;
  expires_on: string;
};

export type NextContentRouteRedirect = {
  source: string;
  destination: string;
  permanent: false;
};

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function parseIsoDate(value: unknown, field: string): string {
  if (typeof value !== 'string' || !ISO_DATE_PATTERN.test(value)) {
    throw new Error(`${field} must use YYYY-MM-DD`);
  }
  const parsed = new Date(`${value}T00:00:00.000Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) {
    throw new Error(`${field} must be a valid ISO date: ${value}`);
  }
  return value;
}

function validateRoute(value: unknown, field: string): string {
  if (
    typeof value !== 'string'
    || !value.startsWith('/')
    || value === '/'
    || value.endsWith('/')
    || value.includes('//')
    || value.split('/').slice(1).some((part) => ['', '.', '..'].includes(part))
  ) {
    throw new Error(`${field} must be a canonical root-relative content route`);
  }
  return value;
}

function validateRedirects(value: unknown): ContentRouteRedirect[] {
  if (value == null) {
    return [];
  }
  if (!Array.isArray(value)) {
    throw new Error('Content redirect registry must be a list');
  }

  const seenSources = new Set<string>();
  return value.map((item, index) => {
    if (typeof item !== 'object' || item === null || Array.isArray(item)) {
      throw new Error(`Content redirect at index ${index} must be a mapping`);
    }
    const candidate = item as Record<string, unknown>;
    const source = validateRoute(candidate.source, 'source');
    const destination = validateRoute(candidate.destination, 'destination');
    const createdOn = parseIsoDate(candidate.created_on, 'created_on');
    const expiresOn = parseIsoDate(candidate.expires_on, 'expires_on');
    if (source === destination) {
      throw new Error(`Content redirect source equals destination: ${source}`);
    }
    if (seenSources.has(source)) {
      throw new Error(`Duplicate content redirect source: ${source}`);
    }
    if (expiresOn <= createdOn) {
      throw new Error(`expires_on must be later than created_on for ${source}`);
    }
    seenSources.add(source);
    return {
      source,
      destination,
      created_on: createdOn,
      expires_on: expiresOn,
    };
  });
}

export function loadActiveContentRouteRedirects(options: {
  filePath?: string;
  currentDate?: Date;
} = {}): ContentRouteRedirect[] {
  const filePath = options.filePath
    ?? path.join(process.cwd(), 'src/content-route-redirects.yaml');
  const currentDate = options.currentDate ?? new Date();
  if (Number.isNaN(currentDate.getTime())) {
    throw new Error('currentDate must be valid');
  }
  const currentIsoDate = currentDate.toISOString().slice(0, 10);
  const redirects = validateRedirects(
    load(readFileSync(filePath, 'utf8')),
  );
  return redirects.filter((redirect) => redirect.expires_on > currentIsoDate);
}

export function expandContentRouteRedirects(
  redirects: ContentRouteRedirect[],
): NextContentRouteRedirect[] {
  return redirects.flatMap(({ source, destination }) => [
    {
      source: `/:locale(ko|en|ja)${source}`,
      destination: `/:locale${destination}`,
      permanent: false,
    },
    {
      source,
      destination,
      permanent: false,
    },
  ]);
}
