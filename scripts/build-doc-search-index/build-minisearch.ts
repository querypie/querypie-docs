import { buildMiniSearchInstance } from '@/lib/doc-search/minisearch-engine';
import type { DocSearchChunk } from '@/lib/doc-search/types';

export function serializeMiniSearchIndex(chunks: DocSearchChunk[]): string {
  const ms = buildMiniSearchInstance(chunks);
  return JSON.stringify(ms);
}
