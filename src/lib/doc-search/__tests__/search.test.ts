import { describe, expect, it } from 'vitest';

import type { DocSearchArtifact } from '@/lib/doc-search/types';
import { searchDocs } from '@/lib/doc-search/search';

const artifact: DocSearchArtifact = {
  version: 1,
  generatedAt: '2026-03-16T00:00:00.000Z',
  lang: 'ko',
  chunks: [
    {
      id: '1',
      pagePath: 'administrator-manual/general/system/integrations/identity-providers',
      url: '/ko/administrator-manual/general/system/integrations/identity-providers',
      title: 'Identity Providers',
      description: 'LDAP 및 SSO 연동',
      headingPath: ['Identity Providers', 'LDAP 연동', 'User Search Filter'],
      content: 'User Search Filter는 사용자가 로그인 시 입력한 아이디를 기반으로 LDAP에서 사용자를 찾는 데 사용할 쿼리입니다.',
      excerpt: 'User Search Filter는 사용자가 로그인 시 입력한 아이디를 기반으로 LDAP에서 사용자를 찾는 데 사용할 쿼리입니다.',
      metadata: {
        lang: 'ko',
        manualType: 'administrator-manual',
        productArea: 'general',
        versionHints: [],
        isUnreleased: false,
      },
    },
    {
      id: '2',
      pagePath: 'administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud',
      url: '/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud',
      title: 'Google Cloud에서 DB 리소스 동기화',
      description: 'GCP 연동 가이드',
      headingPath: ['Google Cloud에서 DB 리소스 동기화', 'QueryPie에서 GCP 연동 정보 등록하기'],
      content: 'Search Filter를 사용하여 동기화하고자 하는 일부 유형의 리소스 목록을 가져올 수 있습니다.',
      excerpt: 'Search Filter를 사용하여 동기화하고자 하는 일부 유형의 리소스 목록을 가져올 수 있습니다.',
      metadata: {
        lang: 'ko',
        manualType: 'administrator-manual',
        productArea: 'databases',
        versionHints: ['11.3.0'],
        isUnreleased: false,
      },
    },
    {
      id: '3',
      pagePath: 'unreleased',
      url: '/ko/unreleased',
      title: 'Unreleased',
      description: '미출시 기능 문서',
      headingPath: ['Unreleased'],
      content: '아직 출시되지 않은 기능 문서를 이곳에서 미리 작성하고 검토합니다.',
      excerpt: '아직 출시되지 않은 기능 문서를 이곳에서 미리 작성하고 검토합니다.',
      metadata: {
        lang: 'ko',
        manualType: 'unreleased',
        productArea: 'unreleased',
        versionHints: [],
        isUnreleased: true,
      },
    },
  ],
};

describe('searchDocs', () => {
  it('ranks exact heading/title matches first', () => {
    const results = searchDocs({ artifact, query: 'LDAP 연동 사용자 검색 필터', topK: 3 });

    expect(results[0]?.pagePath).toBe('administrator-manual/general/system/integrations/identity-providers');
  });

  it('matches section phrases for cloud provider docs', () => {
    const results = searchDocs({ artifact, query: 'GCP DB 리소스 동기화 Search Filter', topK: 3 });

    expect(results[0]?.pagePath).toBe('administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud');
  });

  it('downranks unreleased content by default', () => {
    const results = searchDocs({ artifact, query: '기능 문서', topK: 3 });

    expect(results.at(-1)?.pagePath).toBe('unreleased');
  });

  it('honors manual type filters', () => {
    const results = searchDocs({ artifact, query: 'Search Filter', topK: 3, manualType: 'administrator-manual' });

    expect(results).toHaveLength(2);
    expect(results.every(result => result.metadata.manualType === 'administrator-manual')).toBe(true);
  });
});
