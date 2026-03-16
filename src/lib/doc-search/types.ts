export type ManualType =
  | 'overview'
  | 'user-manual'
  | 'administrator-manual'
  | 'installation'
  | 'release-notes'
  | 'api-reference'
  | 'support'
  | 'unreleased'
  | 'unknown';

export interface DocSearchMetadata {
  lang: string;
  manualType: ManualType;
  productArea: string;
  versionHints: string[];
  isUnreleased: boolean;
}

export interface DocSearchChunk {
  id: string;
  pagePath: string;
  url: string;
  title: string;
  description: string;
  headingPath: string[];
  content: string;
  excerpt: string;
  metadata: DocSearchMetadata;
}

export interface DocSearchPage {
  pagePath: string;
  url: string;
  title: string;
  description: string;
  content: string;
  tableOfContents: string[];
  metadata: DocSearchMetadata;
}

export interface DocSearchArtifact {
  version: number;
  generatedAt: string;
  lang: string;
  chunks: DocSearchChunk[];
}

export interface DocSearchPagesArtifact {
  version: number;
  generatedAt: string;
  lang: string;
  pages: Record<string, DocSearchPage>;
}

export interface SearchDocsParams {
  artifact: DocSearchArtifact;
  query: string;
  topK?: number;
  manualType?: ManualType;
}
