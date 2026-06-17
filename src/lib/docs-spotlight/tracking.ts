import type { DocsSpotlightLocale } from './content';

type DocsSpotlightTrackingItem = {
  href: string;
  id: string;
  title: string;
};

type DocsSpotlightEventName = 'view_promotion' | 'select_promotion' | 'site_notice_dismiss';

type GtagGlobal = typeof globalThis & {
  gtag?: (command: 'event', eventName: DocsSpotlightEventName, params: Record<string, unknown>) => void;
};

const queryPieUrlBase = 'https://www.querypie.com';
const queryPieDomains = new Set(['querypie.com', 'www.querypie.com']);
const localePathPattern = /^\/(en|ja|ko)(\/|$)/;

function createUtmParams(itemId: string) {
  return {
    utm_campaign: itemId,
    utm_content: 'docs_sidebar_card',
    utm_id: `sn_${itemId}`,
    utm_medium: 'notice',
    utm_source: 'qp',
  };
}

function parseUrl(href: string) {
  try {
    return new URL(href);
  } catch {
    return new URL(href, queryPieUrlBase);
  }
}

function isQueryPieOwnedUrl(url: URL) {
  return queryPieDomains.has(url.hostname);
}

function localizeQueryPiePath(pathname: string, locale: DocsSpotlightLocale) {
  if (localePathPattern.test(pathname)) {
    return pathname;
  }

  return `/${locale}${pathname.startsWith('/') ? pathname : `/${pathname}`}`;
}

export function createDocsSpotlightTrackingHref(href: string, itemId: string, locale: DocsSpotlightLocale) {
  const url = parseUrl(href);

  if (!isQueryPieOwnedUrl(url)) {
    return href;
  }

  url.hostname = 'www.querypie.com';
  url.protocol = 'https:';
  url.pathname = localizeQueryPiePath(url.pathname, locale);

  const params = createUtmParams(itemId);

  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.set(key, value);
  });

  return url.toString();
}

const getGtag = () => {
  if (typeof window === 'undefined') {
    return null;
  }

  const candidate = (globalThis as GtagGlobal).gtag;

  return typeof candidate === 'function' ? candidate : null;
};

export function createDocsSpotlightAnalyticsParams(item: DocsSpotlightTrackingItem) {
  const promotionId = `sn_${item.id}`;
  const sharedParams = {
    promotion_id: promotionId,
    promotion_name: item.id,
    creative_slot: 'docs_sidebar_card',
    creative_name: item.title,
    spotlight_id: item.id,
    spotlight_surface: 'docs_sidebar_card',
    spotlight_title: item.title,
    spotlight_destination: item.href,
  };

  return {
    ...sharedParams,
    items: [
      {
        item_id: item.id,
        item_name: item.title,
        promotion_id: promotionId,
        promotion_name: item.id,
        creative_slot: 'docs_sidebar_card',
        creative_name: item.title,
      },
    ],
  };
}

function sendDocsSpotlightAnalyticsEvent(eventName: DocsSpotlightEventName, item: DocsSpotlightTrackingItem) {
  const gtag = getGtag();

  if (!gtag) {
    return;
  }

  try {
    gtag('event', eventName, createDocsSpotlightAnalyticsParams(item));
  } catch {
    // Analytics must never block navigation, dismissal, persistence, or rendering.
  }
}

export function sendDocsSpotlightViewEvent(item: DocsSpotlightTrackingItem) {
  sendDocsSpotlightAnalyticsEvent('view_promotion', item);
}

export function sendDocsSpotlightClickEvent(item: DocsSpotlightTrackingItem) {
  sendDocsSpotlightAnalyticsEvent('select_promotion', item);
}

export function sendDocsSpotlightDismissEvent(item: DocsSpotlightTrackingItem) {
  sendDocsSpotlightAnalyticsEvent('site_notice_dismiss', item);
}
