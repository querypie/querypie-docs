import { render, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import InternalPage, { generateMetadata, generateStaticParams } from './page';

describe('/[lang]/internal page', () => {
  it('generates locale params for internal test pages', () => {
    expect(generateStaticParams()).toEqual([{ lang: 'en' }, { lang: 'ja' }, { lang: 'ko' }]);
  });

  it('renders the Korean internal page title, description, and spotlight preview', async () => {
    const container = document.createElement('div');
    const result = render(await InternalPage({ params: Promise.resolve({ lang: 'ko' }) }), {
      baseElement: container,
      container,
    });

    expect(within(result.container).getByRole('heading', { level: 1, name: '내부 페이지' })).toBeTruthy();
    expect(
      within(result.container).getByText('검토와 구현 참고를 위해 유지 중인 내부 컴포넌트 및 페이지 예시 목록입니다.'),
    ).toBeTruthy();
    expect(within(result.container).queryByRole('list')).not.toBeInTheDocument();
    expect(within(result.container).getByTestId('docs-spotlight-card')).toBeTruthy();
  });

  it('exposes the localized spotlight preview on the internal page', async () => {
    const container = document.createElement('div');
    const result = render(await InternalPage({ params: Promise.resolve({ lang: 'ko' }) }), {
      baseElement: container,
      container,
    });

    expect(within(result.container).getByTestId('docs-spotlight-card')).toBeTruthy();
    expect(within(result.container).getByText('AI Work OS: 새로운 지능이 기업 안에서 일하는 방식')).toBeTruthy();
  });

  it('uses the same copy for route metadata', async () => {
    await expect(generateMetadata({ params: Promise.resolve({ lang: 'ko' }) })).resolves.toMatchObject({
      description: '검토와 구현 참고를 위해 유지 중인 내부 컴포넌트 및 페이지 예시 목록입니다.',
      title: '내부 페이지',
    });
  });

  it('falls back to English metadata when static generation omits params', async () => {
    await expect(generateMetadata({})).resolves.toMatchObject({
      description: 'A list of internal component and page examples maintained for review and implementation reference.',
      title: 'Internal Pages',
    });
  });
});
