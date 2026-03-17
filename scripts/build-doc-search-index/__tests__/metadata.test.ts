import { describe, expect, it } from 'vitest';

import { inferDocMetadata } from '../metadata';

// 테스트에서 사용하는 헬퍼: inferDocMetadata 호출을 간결하게 만듭니다
function makeMetadata(filePath: string, lang = 'ko') {
  return inferDocMetadata({ filePath, lang, title: 'Test', description: '', content: '' });
}

describe('inferDocMetadata — pagePath 생성', () => {
  it('일반 파일의 pagePath는 lang prefix와 .mdx 확장자를 제거합니다', () => {
    const metadata = makeMetadata('src/content/ko/user-manual/overview.mdx');

    expect(metadata.pagePath).toBe('user-manual/overview');
    expect(metadata.url).toBe('/ko/user-manual/overview');
  });

  it('en, ja 같은 다른 lang도 prefix를 올바르게 제거합니다', () => {
    expect(makeMetadata('src/content/en/user-manual/overview.mdx', 'en').pagePath).toBe(
      'user-manual/overview',
    );
    expect(makeMetadata('src/content/ja/user-manual/overview.mdx', 'ja').pagePath).toBe(
      'user-manual/overview',
    );
  });
});

describe('inferDocMetadata — index.mdx pagePath 정규화 (#930 버그 수정)', () => {
  /**
   * 수정 전 동작 (버그):
   *   src/content/ko/user-manual/index.mdx
   *     → pagePath: 'user-manual/index'
   *     → url:      '/ko/user-manual/index'
   *
   * 이 경우 MCP consumer가 get_doc_page('user-manual')을 호출하면 NOT FOUND가 됩니다.
   * 사이트 URL은 /ko/user-manual 인데 실제 저장된 키는 'user-manual/index'이기 때문입니다.
   *
   * 수정 후 동작:
   *   src/content/ko/user-manual/index.mdx
   *     → pagePath: 'user-manual'
   *     → url:      '/ko/user-manual'
   */
  it('섹션 루트 index.mdx의 pagePath에서 /index suffix를 제거합니다', () => {
    const metadata = makeMetadata('src/content/ko/user-manual/index.mdx');

    // 수정 전: 'user-manual/index' → get_doc_page('user-manual') 실패
    // 수정 후: 'user-manual'       → get_doc_page('user-manual') 성공
    expect(metadata.pagePath).toBe('user-manual');
    expect(metadata.url).toBe('/ko/user-manual');
    expect(metadata.pagePath).not.toContain('/index');
  });

  it('중첩 경로의 index.mdx도 /index suffix를 제거합니다', () => {
    // 예: user-manual/databases/index.mdx → pagePath: 'user-manual/databases'
    //     get_doc_page('user-manual/databases') 가 올바르게 동작해야 합니다
    const metadata = makeMetadata('src/content/ko/user-manual/databases/index.mdx');

    expect(metadata.pagePath).toBe('user-manual/databases');
    expect(metadata.url).toBe('/ko/user-manual/databases');
    expect(metadata.manualType).toBe('user-manual');
    expect(metadata.productArea).toBe('databases');
  });

  it('깊은 중첩 경로의 index.mdx도 올바르게 처리합니다', () => {
    const metadata = makeMetadata(
      'src/content/ko/administrator-manual/databases/connection-management/index.mdx',
    );

    expect(metadata.pagePath).toBe('administrator-manual/databases/connection-management');
    expect(metadata.url).toBe('/ko/administrator-manual/databases/connection-management');
    expect(metadata.manualType).toBe('administrator-manual');
  });

  it('루트 index.mdx는 슬래시가 없어 /index regex에 걸리지 않으므로 pagePath가 index로 유지됩니다', () => {
    // src/content/ko/index.mdx → .replace(/\/index$/, '') 는 'index'에 미적용
    // (패턴이 슬래시로 시작하는 /index를 찾기 때문)
    const metadata = makeMetadata('src/content/ko/index.mdx');

    expect(metadata.pagePath).toBe('index');
    expect(metadata.url).toBe('/ko/index');
  });

  it('파일명이 index가 아닌 경우 영향 없습니다', () => {
    // 'indexing.mdx' 같이 index로 시작하지만 /index suffix가 아닌 경우
    const metadata = makeMetadata('src/content/ko/user-manual/indexing.mdx');

    expect(metadata.pagePath).toBe('user-manual/indexing');
    expect(metadata.url).toBe('/ko/user-manual/indexing');
  });
});

describe('inferDocMetadata — manualType 추론', () => {
  it.each([
    ['overview', 'src/content/ko/overview/intro.mdx'],
    ['user-manual', 'src/content/ko/user-manual/intro.mdx'],
    ['administrator-manual', 'src/content/ko/administrator-manual/intro.mdx'],
    ['installation', 'src/content/ko/installation/intro.mdx'],
    ['release-notes', 'src/content/ko/release-notes/v11.mdx'],
    ['api-reference', 'src/content/ko/api-reference/intro.mdx'],
    ['support', 'src/content/ko/support/faq.mdx'],
    ['unreleased', 'src/content/ko/unreleased/new-feature.mdx'],
  ] as const)('%s 섹션은 manualType이 올바르게 추론됩니다', (expectedType, filePath) => {
    const metadata = makeMetadata(filePath);

    expect(metadata.manualType).toBe(expectedType);
  });

  it('알 수 없는 섹션은 manualType이 unknown입니다', () => {
    const metadata = makeMetadata('src/content/ko/unknown-section/page.mdx');

    expect(metadata.manualType).toBe('unknown');
  });
});
