import fs from 'node:fs';
import path from 'node:path';

import type { DocSearchArtifact, DocSearchPagesArtifact } from '@/lib/doc-search/types';

let artifactCache: DocSearchArtifact | null = null;
let pagesCache: DocSearchPagesArtifact | null = null;

function readJsonFile<T>(filePath: string): T {
  return JSON.parse(fs.readFileSync(filePath, 'utf8')) as T;
}

export function loadDocSearchArtifact(lang = 'ko'): DocSearchArtifact {
  if (!artifactCache) {
    artifactCache = readJsonFile<DocSearchArtifact>(path.join(process.cwd(), 'public', '_doc-search', `${lang}-index.json`));
  }
  return artifactCache;
}

export function loadDocSearchPagesArtifact(lang = 'ko'): DocSearchPagesArtifact {
  if (!pagesCache) {
    pagesCache = readJsonFile<DocSearchPagesArtifact>(path.join(process.cwd(), 'public', '_doc-search', `${lang}-pages.json`));
  }
  return pagesCache;
}
