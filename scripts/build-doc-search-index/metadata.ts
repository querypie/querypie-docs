import type { DocSearchMetadata } from '@/lib/doc-search/types';

export interface InferredDocMetadata extends DocSearchMetadata {
  pagePath: string;
  url: string;
}

const VERSION_PATTERN = /\b\d+\.\d+\.\d+\b/g;

function stripContentPrefix(filePath: string): string {
  return filePath
    .replace(/^src\/content\/[a-z]{2}\//, '')
    .replace(/\.mdx$/, '')
    .replace(/\/index$/, '');
}

function inferManualTypeFromPath(pagePath: string): DocSearchMetadata['manualType'] {
  const firstSegment = pagePath.split('/')[0];
  switch (firstSegment) {
    case 'overview':
    case 'user-manual':
    case 'administrator-manual':
    case 'installation':
    case 'release-notes':
    case 'api-reference':
    case 'support':
    case 'unreleased':
      return firstSegment;
    default:
      return 'unknown';
  }
}

function inferProductArea(pagePath: string, manualType: DocSearchMetadata['manualType']): string {
  const segments = pagePath.split('/');
  return segments[1] || manualType;
}

export function inferDocMetadata(input: {
  filePath: string;
  lang: string;
  title: string;
  description: string;
  content: string;
}): InferredDocMetadata {
  const pagePath = stripContentPrefix(input.filePath);
  const manualType = inferManualTypeFromPath(pagePath);
  const productArea = inferProductArea(pagePath, manualType);
  const versionHints = Array.from(new Set(input.content.match(VERSION_PATTERN) ?? []));
  const isUnreleased = manualType === 'unreleased' || pagePath.startsWith('unreleased');

  return {
    pagePath,
    url: `/${input.lang}/${pagePath}`,
    lang: input.lang,
    manualType,
    productArea,
    versionHints,
    isUnreleased,
  };
}
