import { describe, expect, it } from 'vitest';

import { docsSpotlightContent, getActiveDocsSpotlightContent } from './content';

describe('docs spotlight content', () => {
  it('uses the current corp-web-app spotlight ids and localized labels', () => {
    expect(docsSpotlightContent.en.items.map(item => item.id)).toEqual([
      'iso-42001-certification',
      'lingo-release',
      'notepie-release',
      'ai-work-os-enterprise-intelligence',
    ]);
    expect(docsSpotlightContent.ko.spotlightLabel).toBe('하이라이트');
    expect(docsSpotlightContent.ja.spotlightCtaLabel).toBe('詳しく見る');
  });

  it('filters active items inclusively and keeps the newest active item first', () => {
    expect(getActiveDocsSpotlightContent('en', { today: '2026-06-17', random: () => 0 })?.items.map(item => item.id)).toEqual([
      'notepie-release',
      'iso-42001-certification',
      'lingo-release',
    ]);
    expect(getActiveDocsSpotlightContent('ko', { today: '2026-06-17', random: () => 0 })?.items[0]?.id).toBe(
      'ai-work-os-enterprise-intelligence',
    );
    expect(getActiveDocsSpotlightContent('en', { today: '2026-07-04', random: () => 0 })?.items.map(item => item.id)).toEqual(
      expect.arrayContaining(['iso-42001-certification']),
    );
    expect(getActiveDocsSpotlightContent('en', { today: '2026-07-09', random: () => 0 })?.items.map(item => item.id)).toEqual([
      'notepie-release',
    ]);
  });

  it('returns null when no item is active', () => {
    expect(getActiveDocsSpotlightContent('en', { today: '2026-07-10' })).toBeNull();
  });

  it('falls back to English content for unknown locales', () => {
    expect(getActiveDocsSpotlightContent('unknown', { today: '2026-06-17' })?.ariaLabel).toBe(
      'Latest company announcements',
    );
  });
});
