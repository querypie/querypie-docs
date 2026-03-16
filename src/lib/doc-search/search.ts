import type { DocSearchChunk, SearchDocsParams } from '@/lib/doc-search/types';

function normalizeText(input: string): string {
  return input.toLowerCase().replace(/\s+/g, ' ').trim();
}

function tokenize(input: string): string[] {
  return normalizeText(input)
    .split(/[^\p{L}\p{N}.+#-]+/u)
    .map(token => token.trim())
    .filter(Boolean);
}

function scoreChunk(query: string, queryTokens: string[], chunk: DocSearchChunk): number {
  const title = normalizeText(chunk.title);
  const heading = normalizeText(chunk.headingPath.join(' '));
  const content = normalizeText(chunk.content);
  let score = 0;
  let matched = false;

  for (const token of queryTokens) {
    if (title.includes(token)) { score += 12; matched = true; }
    if (heading.includes(token)) { score += 8; matched = true; }
    if (content.includes(token)) { score += 4; matched = true; }
  }

  if (title.includes(query)) { score += 40; matched = true; }
  if (heading.includes(query)) { score += 28; matched = true; }
  if (content.includes(query)) { score += 16; matched = true; }

  if (!matched) return 0;

  if (chunk.metadata.isUnreleased) score -= 10;
  score += Math.max(0, 6 - Math.floor(chunk.content.length / 400));

  return score;
}

export function searchDocs({ artifact, query, topK = 5, manualType }: SearchDocsParams): DocSearchChunk[] {
  const normalizedQuery = normalizeText(query);
  const queryTokens = tokenize(query);
  if (!normalizedQuery || queryTokens.length === 0) {
    return [];
  }

  return artifact.chunks
    .filter(chunk => !manualType || chunk.metadata.manualType === manualType)
    .map(chunk => ({ chunk, score: scoreChunk(normalizedQuery, queryTokens, chunk) }))
    .filter(entry => entry.score > 0)
    .sort((a, b) => b.score - a.score || a.chunk.title.localeCompare(b.chunk.title, 'ko'))
    .slice(0, Math.min(topK, 10))
    .map(entry => ({ ...entry.chunk, score: entry.score } as DocSearchChunk & { score: number })) as DocSearchChunk[];
}
