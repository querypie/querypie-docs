import type { DocSearchPage } from '@/lib/doc-search/types';
import { loadDocSearchPagesArtifact } from '@/lib/doc-search/load-index';

export function getDocPage(pagePath: string, lang = 'ko'): DocSearchPage | null {
  const artifact = loadDocSearchPagesArtifact(lang);
  return artifact.pages[pagePath] ?? null;
}
