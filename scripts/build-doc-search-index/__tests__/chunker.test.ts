import { describe, expect, it } from 'vitest';

import { parseMdxDocument } from '../mdx-parser';
import { buildChunksFromDocument } from '../chunker';
import { inferDocMetadata } from '../metadata';

const sampleMdx = `---
title: 'Google Cloud에서 DB 리소스 동기화'
description: 'GCP 연동 가이드'
confluenceUrl: 'https://example.com/confluence'
---

import { Callout } from 'nextra/components'

# Google Cloud에서 DB 리소스 동기화

### Overview

QueryPie에서는 데이터베이스 등록 및 관리를 위한 Google Cloud(GCP) 연동을 지원합니다.

<Callout type="info">
11.3.0에서 특정 태그가 있는 리소스만 동기화할 수 있도록 Search Filter 기능이 추가되었습니다.
</Callout>

### QueryPie에서 GCP 연동 정보 등록하기

1. Database 설정 메뉴에서 Cloud Provider 메뉴로 이동합니다.
2. \

aaa
3. **Search Filter** 를 사용하여 동기화하고자 하는 일부 유형의 리소스 목록을 가져올 수 있습니다.

<figure>
<img src="/foo.png" alt="Cloud Provider 화면" />
<figcaption>Cloud Provider 화면</figcaption>
</figure>
`;

describe('parseMdxDocument', () => {
  it('strips frontmatter/imports and keeps searchable text', () => {
    const document = parseMdxDocument(sampleMdx, {
      filePath: 'src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud.mdx',
      lang: 'ko',
    });

    expect(document.title).toBe('Google Cloud에서 DB 리소스 동기화');
    expect(document.description).toBe('GCP 연동 가이드');
    expect(document.content).not.toContain("import { Callout }");
    expect(document.content).not.toContain('---');
    expect(document.content).toContain('11.3.0에서 특정 태그가 있는 리소스만 동기화할 수 있도록 Search Filter 기능이 추가되었습니다.');
    expect(document.content).toContain('Cloud Provider 화면');
  });
});

describe('inferDocMetadata', () => {
  it('infers path-driven metadata and version hints', () => {
    const metadata = inferDocMetadata({
      filePath: 'src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud.mdx',
      lang: 'ko',
      title: 'Google Cloud에서 DB 리소스 동기화',
      description: 'GCP 연동 가이드',
      content: sampleMdx,
    });

    expect(metadata.url).toBe('/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud');
    expect(metadata.pagePath).toBe('administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud');
    expect(metadata.manualType).toBe('administrator-manual');
    expect(metadata.productArea).toBe('databases');
    expect(metadata.versionHints).toContain('11.3.0');
    expect(metadata.isUnreleased).toBe(false);
  });
});

describe('buildChunksFromDocument', () => {
  it('builds heading-based chunks with breadcrumbs and rich text', () => {
    const document = parseMdxDocument(sampleMdx, {
      filePath: 'src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud.mdx',
      lang: 'ko',
    });
    const metadata = inferDocMetadata({
      filePath: document.filePath,
      lang: document.lang,
      title: document.title,
      description: document.description,
      content: document.content,
    });

    const chunks = buildChunksFromDocument(document, metadata);

    expect(chunks.length).toBeGreaterThanOrEqual(2);
    expect(chunks[0].headingPath).toEqual(['Google Cloud에서 DB 리소스 동기화', 'Overview']);
    expect(chunks[0].content).toContain('QueryPie에서는 데이터베이스 등록 및 관리를 위한 Google Cloud(GCP) 연동을 지원합니다.');

    const registrationChunk = chunks.find(chunk => chunk.headingPath.includes('QueryPie에서 GCP 연동 정보 등록하기'));
    expect(registrationChunk).toBeDefined();
    expect(registrationChunk?.content).toContain('Search Filter');
    expect(registrationChunk?.content).toContain('Cloud Provider 화면');
    expect(registrationChunk?.excerpt.length).toBeLessThanOrEqual(220);
  });
});
