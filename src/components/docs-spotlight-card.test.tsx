import { act, fireEvent, render, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DocsSpotlightCard } from './docs-spotlight-card';
import { DOCS_SPOTLIGHT_STORAGE_KEY } from '@/lib/docs-spotlight/storage';
import type { ActiveDocsSpotlightContent } from '@/lib/docs-spotlight/content';

const items: ActiveDocsSpotlightContent['items'] = [
  {
    id: 'iso-42001-certification',
    date: '2026-06-04',
    href: '/news/24/iso-42001-certification-announcement',
    imageAlt: 'ISO 42001 announcement',
    imageSrc: '/spotlight/iso-42001-certification/thumbnail.png',
    title: 'ISO/IEC 42001 Certification for AI Management System',
    spotlightMeta: 'June 4, 2026',
  },
  {
    id: 'lingo-release',
    date: '2026-06-05',
    href: '/news/26/lingo-launch',
    imageAlt: 'Lingo launch',
    imageSrc: '/spotlight/lingo-release/hero-en.png',
    title: 'Lingo: AI Real-Time Interpretation Service',
    spotlightMeta: 'June 5, 2026',
  },
];

const content: ActiveDocsSpotlightContent = {
  ariaLabel: 'Latest company announcements',
  items,
  nextLabel: 'Next announcement',
  previousLabel: 'Previous announcement',
  spotlightCtaLabel: 'Read full story',
  spotlightDismissLabel: 'Dismiss spotlight',
  spotlightLabel: 'Spotlight',
};

function readSpotlightStorageRecord(id: string) {
  const rawValue = window.localStorage.getItem(DOCS_SPOTLIGHT_STORAGE_KEY);

  if (!rawValue) {
    throw new Error(`Expected ${DOCS_SPOTLIGHT_STORAGE_KEY} to exist`);
  }

  return JSON.parse(rawValue)[id];
}

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();

  return {
    clear: () => values.clear(),
    getItem: key => values.get(key) ?? null,
    key: index => Array.from(values.keys())[index] ?? null,
    get length() {
      return values.size;
    },
    removeItem: key => values.delete(key),
    setItem: (key, value) => values.set(key, String(value)),
  } as Storage;
}

function clickLinkWithoutNavigation(element: HTMLElement) {
  element.addEventListener('click', event => event.preventDefault(), { once: true });
  fireEvent.click(element);
}

describe('DocsSpotlightCard', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-06-12T00:00:00.000Z'));
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: createMemoryStorage(),
    });
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: false,
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('renders the first active item after browser visibility state is checked', () => {
    const container = document.createElement('div');
    const result = render(<DocsSpotlightCard content={content} locale="en" />, {
      baseElement: container,
      container,
    });

    expect(result.container.querySelector('[data-testid="docs-spotlight-card"]')).toBeTruthy();
    expect(within(result.container).getByText('ISO/IEC 42001 Certification for AI Management System')).toBeTruthy();
    expect(within(result.container).getByAltText('ISO 42001 announcement')).toHaveAttribute(
      'src',
      '/spotlight/iso-42001-certification/thumbnail.png',
    );

    const link = within(result.container).getByRole('link', { name: /ISO\/IEC 42001/ });
    expect(link).toHaveAttribute(
      'href',
      expect.stringContaining('https://www.querypie.com/en/news/24/iso-42001-certification-announcement?'),
    );
  });

  it('rotates, pauses on hover, and supports manual previous and next controls', () => {
    const container = document.createElement('div');
    const result = render(<DocsSpotlightCard content={content} locale="en" rotationIntervalMs={1000} />, {
      baseElement: container,
      container,
    });

    fireEvent.mouseEnter(within(result.container).getByTestId('docs-spotlight-card'));
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(within(result.container).getByText('ISO/IEC 42001 Certification for AI Management System')).toBeTruthy();

    fireEvent.mouseLeave(within(result.container).getByTestId('docs-spotlight-card'));
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(within(result.container).getByText('Lingo: AI Real-Time Interpretation Service')).toBeTruthy();

    fireEvent.click(within(result.container).getByRole('button', { name: 'Previous announcement' }));
    expect(within(result.container).getByText('ISO/IEC 42001 Certification for AI Management System')).toBeTruthy();

    fireEvent.click(within(result.container).getByRole('button', { name: 'Next announcement' }));
    expect(within(result.container).getByText('Lingo: AI Real-Time Interpretation Service')).toBeTruthy();
  });

  it('stores viewed and dismissed records while keeping failures recoverable', () => {
    const container = document.createElement('div');
    const result = render(<DocsSpotlightCard content={content} locale="en" />, {
      baseElement: container,
      container,
    });

    clickLinkWithoutNavigation(within(result.container).getByRole('link', { name: /ISO\/IEC 42001/ }));
    expect(readSpotlightStorageRecord('iso-42001-certification')).toEqual({
      disposition: 'viewed',
      updatedAt: '2026-06-12T00:00:00.000Z',
      expiresAt: '2026-07-12T00:00:00.000Z',
    });

    fireEvent.click(within(result.container).getByRole('button', { name: 'Dismiss spotlight' }));
    expect(within(result.container).queryByTestId('docs-spotlight-card')).not.toBeInTheDocument();
  });

  it('renders nothing when all active items are suppressed', () => {
    window.localStorage.setItem(
      DOCS_SPOTLIGHT_STORAGE_KEY,
      JSON.stringify({
        'iso-42001-certification': {
          disposition: 'viewed',
          updatedAt: '2026-06-01T00:00:00.000Z',
          expiresAt: '2026-07-01T00:00:00.000Z',
        },
        'lingo-release': {
          disposition: 'dismissed',
          updatedAt: '2026-06-01T00:00:00.000Z',
          expiresAt: '2026-07-01T00:00:00.000Z',
        },
      }),
    );

    const container = document.createElement('div');
    const result = render(<DocsSpotlightCard content={content} locale="en" />, {
      baseElement: container,
      container,
    });

    expect(within(result.container).queryByTestId('docs-spotlight-card')).not.toBeInTheDocument();
  });
});
