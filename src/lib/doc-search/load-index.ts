import fs from 'node:fs';
import path from 'node:path';

import MiniSearch from 'minisearch';

import type { DocSearchArtifact, DocSearchChunk, DocSearchPagesArtifact } from '@/lib/doc-search/types';
import { MINISEARCH_LOAD_OPTIONS } from '@/lib/doc-search/minisearch-engine';

const artifactCache = new Map<string, DocSearchArtifact>();
const pagesCache = new Map<string, DocSearchPagesArtifact>();
const miniSearchCache = new Map<string, MiniSearch<DocSearchChunk>>();

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

export function loadMiniSearchIndex(lang = 'ko'): MiniSearch<DocSearchChunk> {
  if (!miniSearchCache.has(lang)) {
    const json = fs.readFileSync(
      path.join(process.cwd(), 'public', '_doc-search', `${lang}-minisearch.json`),
      'utf8',
    );
    miniSearchCache.set(lang, MiniSearch.loadJSON<DocSearchChunk>(json, MINISEARCH_LOAD_OPTIONS));
  }
  return miniSearchCache.get(lang)!;
}
