import fs from 'node:fs';
import path from 'node:path';

import type { DocSearchArtifact, DocSearchPagesArtifact } from '@/lib/doc-search/types';

const artifactCache = new Map<string, DocSearchArtifact>();
const pagesCache = new Map<string, DocSearchPagesArtifact>();

function readJsonFile<T>(filePath: string): T {
  return JSON.parse(fs.readFileSync(filePath, 'utf8')) as T;
}

export function loadDocSearchArtifact(lang = 'ko'): DocSearchArtifact {
  if (!artifactCache.has(lang)) {
    artifactCache.set(lang, readJsonFile<DocSearchArtifact>(path.join(process.cwd(), 'public', '_doc-search', `${lang}-index.json`)));
  }
  return artifactCache.get(lang)!;
}

export function loadDocSearchPagesArtifact(lang = 'ko'): DocSearchPagesArtifact {
  if (!pagesCache.has(lang)) {
    pagesCache.set(lang, readJsonFile<DocSearchPagesArtifact>(path.join(process.cwd(), 'public', '_doc-search', `${lang}-pages.json`)));
  }
  return pagesCache.get(lang)!;
}
