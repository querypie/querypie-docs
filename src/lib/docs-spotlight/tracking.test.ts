import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  createDocsSpotlightAnalyticsParams,
  createDocsSpotlightTrackingHref,
  sendDocsSpotlightClickEvent,
  sendDocsSpotlightDismissEvent,
  sendDocsSpotlightViewEvent,
} from './tracking';

const item = {
  id: 'lingo-release',
  href: '/news/26/lingo-launch',
  title: 'Lingo: AI Real-Time Interpretation Service',
};

const readParams = (href: string) => new URL(href).searchParams;

describe('docs spotlight tracking', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('adds docs sidebar UTM values to QueryPie-owned relative URLs and preserves hash', () => {
    const href = createDocsSpotlightTrackingHref('/news/26/lingo-launch?ref=hero#demo', 'lingo-release', 'en');
    const params = readParams(href);

    expect(href).toMatch(/^https:\/\/www\.querypie\.com\/en\/news\/26\/lingo-launch\?/);
    expect(params.get('ref')).toBe('hero');
    expect(params.get('utm_source')).toBe('qp');
    expect(params.get('utm_medium')).toBe('notice');
    expect(params.get('utm_campaign')).toBe('lingo-release');
    expect(params.get('utm_content')).toBe('docs_sidebar_card');
    expect(params.get('utm_id')).toBe('sn_lingo-release');
    expect(href.endsWith('#demo')).toBe(true);
  });

  it('does not rewrite external URLs', () => {
    const href = 'https://example.com/event?utm_source=partner#details';

    expect(createDocsSpotlightTrackingHref(href, 'external-event', 'ko')).toBe(href);
  });

  it('builds and sends GA promotion events without throwing when gtag is unavailable', () => {
    expect(createDocsSpotlightAnalyticsParams(item)).toMatchObject({
      promotion_id: 'sn_lingo-release',
      promotion_name: 'lingo-release',
      creative_slot: 'docs_sidebar_card',
      creative_name: 'Lingo: AI Real-Time Interpretation Service',
      spotlight_id: 'lingo-release',
      spotlight_surface: 'docs_sidebar_card',
      spotlight_destination: '/news/26/lingo-launch',
    });

    const gtagMock = vi.fn();
    vi.stubGlobal('gtag', gtagMock);

    sendDocsSpotlightViewEvent(item);
    sendDocsSpotlightClickEvent(item);
    sendDocsSpotlightDismissEvent(item);

    expect(gtagMock).toHaveBeenNthCalledWith(1, 'event', 'view_promotion', expect.any(Object));
    expect(gtagMock).toHaveBeenNthCalledWith(2, 'event', 'select_promotion', expect.any(Object));
    expect(gtagMock).toHaveBeenNthCalledWith(3, 'event', 'site_notice_dismiss', expect.any(Object));

    vi.stubGlobal('gtag', undefined);
    expect(() => sendDocsSpotlightClickEvent(item)).not.toThrow();
  });
});
