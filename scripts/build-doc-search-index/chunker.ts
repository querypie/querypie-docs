import crypto from 'node:crypto';

import type { DocSearchChunk } from '@/lib/doc-search/types';
import type { ParsedMdxDocument } from './mdx-parser';
import type { InferredDocMetadata } from './metadata';

function makeExcerpt(content: string, maxLength = 220): string {
  return content.length <= maxLength ? content : `${content.slice(0, maxLength - 1).trim()}…`;
}

function finalizeChunk(
  chunks: DocSearchChunk[],
  document: ParsedMdxDocument,
  metadata: InferredDocMetadata,
  headingPath: string[],
  buffer: string[],
): void {
  const content = buffer.join('\n').trim();
  if (!content) return;

  chunks.push({
    id: crypto.createHash('sha1').update(`${metadata.pagePath}:${headingPath.join('>')}:${content}`).digest('hex'),
    pagePath: metadata.pagePath,
    url: metadata.url,
    title: document.title,
    description: document.description,
    headingPath,
    content,
    excerpt: makeExcerpt(content),
    metadata: {
      lang: metadata.lang,
      manualType: metadata.manualType,
      productArea: metadata.productArea,
      versionHints: metadata.versionHints,
      isUnreleased: metadata.isUnreleased,
    },
  });
}

export function buildChunksFromDocument(document: ParsedMdxDocument, metadata: InferredDocMetadata): DocSearchChunk[] {
  const lines = document.content.split('\n');
  const chunks: DocSearchChunk[] = [];
  let currentHeadingPath = [document.title];
  let buffer: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      if (buffer.at(-1) !== '') buffer.push('');
      continue;
    }

    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(line);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = headingMatch[2].trim();

      if (level === 1) {
        currentHeadingPath = [headingText];
        continue;
      }

      finalizeChunk(chunks, document, metadata, currentHeadingPath, buffer);
      buffer = [];

      const parentTitle = currentHeadingPath[0] || document.title;
      if (level === 2 || level === 3) {
        currentHeadingPath = [parentTitle, headingText];
      } else {
        currentHeadingPath = [...currentHeadingPath.slice(0, 2), headingText];
      }
      continue;
    }

    buffer.push(line);
  }

  finalizeChunk(chunks, document, metadata, currentHeadingPath, buffer);
  return chunks;
}
