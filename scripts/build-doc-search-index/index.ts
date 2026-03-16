import fs from 'node:fs';
import path from 'node:path';

import type { DocSearchArtifact, DocSearchPage, DocSearchPagesArtifact } from '@/lib/doc-search/types';
import { extractTableOfContents } from '@/lib/doc-search/normalize-mdx';
import { buildChunksFromDocument } from './chunker';
import { inferDocMetadata } from './metadata';
import { parseMdxDocument } from './mdx-parser';

const SUPPORTED_LANGS = ['ko', 'en', 'ja'] as const;
type SupportedLang = (typeof SUPPORTED_LANGS)[number];

const OUTPUT_ROOT = path.join(process.cwd(), 'public', '_doc-search');

function listMdxFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) return listMdxFiles(fullPath);
    return entry.name.endsWith('.mdx') ? [fullPath] : [];
  });
}

function ensureOutputDir(): void {
  fs.mkdirSync(OUTPUT_ROOT, { recursive: true });
}

function toRepoRelative(filePath: string): string {
  return path.relative(process.cwd(), filePath).split(path.sep).join('/');
}

export function buildDocSearchArtifacts(lang: SupportedLang): { index: DocSearchArtifact; pages: DocSearchPagesArtifact } {
  const contentRoot = path.join(process.cwd(), 'src', 'content', lang);
  const files = listMdxFiles(contentRoot);
  const chunks = [] as DocSearchArtifact['chunks'];
  const pages: Record<string, DocSearchPage> = {};
  const generatedAt = new Date().toISOString();

  for (const file of files) {
    const source = fs.readFileSync(file, 'utf8');
    const relativeFilePath = toRepoRelative(file);
    const document = parseMdxDocument(source, { filePath: relativeFilePath, lang });
    const metadata = inferDocMetadata({
      filePath: relativeFilePath,
      lang,
      title: document.title,
      description: document.description,
      content: document.content,
    });

    chunks.push(...buildChunksFromDocument(document, metadata));
    pages[metadata.pagePath] = {
      pagePath: metadata.pagePath,
      url: metadata.url,
      title: document.title,
      description: document.description,
      content: document.content,
      tableOfContents: extractTableOfContents(source),
      metadata: {
        lang: metadata.lang,
        manualType: metadata.manualType,
        productArea: metadata.productArea,
        versionHints: metadata.versionHints,
        isUnreleased: metadata.isUnreleased,
      },
    };
  }

  return {
    index: {
      version: 1,
      generatedAt,
      lang,
      chunks,
    },
    pages: {
      version: 1,
      generatedAt,
      lang,
      pages,
    },
  };
}

export function writeDocSearchArtifacts(langs: SupportedLang[] = [...SUPPORTED_LANGS]): void {
  ensureOutputDir();
  for (const lang of langs) {
    const { index, pages } = buildDocSearchArtifacts(lang);
    fs.writeFileSync(path.join(OUTPUT_ROOT, `${lang}-index.json`), JSON.stringify(index));
    fs.writeFileSync(path.join(OUTPUT_ROOT, `${lang}-pages.json`), JSON.stringify(pages));
    console.log(`Generated docs search artifacts for lang: ${lang}`);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const langArg = process.argv[2] as SupportedLang | undefined;
  const langs = langArg ? [langArg] : [...SUPPORTED_LANGS];
  writeDocSearchArtifacts(langs);
}
