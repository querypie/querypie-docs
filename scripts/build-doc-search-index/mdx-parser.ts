import matter from 'gray-matter';

import { normalizeMdxForLLM } from '@/lib/doc-search/normalize-mdx';

export interface ParsedMdxDocument {
  filePath: string;
  lang: string;
  title: string;
  description: string;
  content: string;
  rawContent: string;
}

export function parseMdxDocument(
  source: string,
  options: { filePath: string; lang: string },
): ParsedMdxDocument {
  const parsed = matter(source);
  const normalizedContent = normalizeMdxForLLM(source);
  const headingTitle = normalizedContent
    .split('\n')
    .find(line => line.startsWith('# '))
    ?.replace(/^#\s+/, '')
    .trim();

  const title = String(parsed.data.title || headingTitle || options.filePath.split('/').pop()?.replace(/\.mdx$/, '') || 'Untitled');
  const description = String(parsed.data.description || '');

  return {
    filePath: options.filePath,
    lang: options.lang,
    title,
    description,
    content: normalizedContent,
    rawContent: source,
  };
}
