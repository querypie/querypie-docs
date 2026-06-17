'use client';

import { ChevronLeftIcon, ChevronRightIcon, XMarkIcon } from '@heroicons/react/24/outline';
import type { FocusEvent } from 'react';
import { useEffect, useRef, useState } from 'react';

import type { ActiveDocsSpotlightContent, DocsSpotlightLocale } from '@/lib/docs-spotlight/content';
import {
  getDocsSpotlightBrowserLocalStorage,
  readDocsSpotlightVisibilityState,
  writeDocsSpotlightVisibilityRecord,
  type DocsSpotlightDisposition,
} from '@/lib/docs-spotlight/storage';
import {
  createDocsSpotlightTrackingHref,
  sendDocsSpotlightClickEvent,
  sendDocsSpotlightDismissEvent,
  sendDocsSpotlightViewEvent,
} from '@/lib/docs-spotlight/tracking';

import styles from './docs-spotlight-card.module.css';

type DocsSpotlightCardProps = {
  content: ActiveDocsSpotlightContent | null;
  locale: DocsSpotlightLocale;
  rotationIntervalMs?: number;
};

const defaultRotationIntervalMs = 4000;
const hiddenSpotlightCardViewportQuery = '(max-width: 1023px)';

function prefersReducedMotion() {
  return (
    typeof globalThis.matchMedia === 'function' && globalThis.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

function isSpotlightCardInVisibleViewport() {
  return (
    typeof globalThis.matchMedia !== 'function' || !globalThis.matchMedia(hiddenSpotlightCardViewportQuery).matches
  );
}

export function DocsSpotlightCard({
  content,
  locale,
  rotationIntervalMs = defaultRotationIntervalMs,
}: DocsSpotlightCardProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [hasCheckedVisibilityState, setHasCheckedVisibilityState] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [renderableItems, setRenderableItems] = useState(content?.items ?? []);
  const viewedItemIdsRef = useRef<Set<string>>(new Set());
  const activeItem = renderableItems[activeIndex] ?? renderableItems[0];
  const canRotate = renderableItems.length > 1 && rotationIntervalMs > 0;

  useEffect(() => {
    if (!content) {
      setRenderableItems([]);
      setHasCheckedVisibilityState(true);
      return;
    }

    const storage = getDocsSpotlightBrowserLocalStorage();
    const visibilityState = storage ? readDocsSpotlightVisibilityState(storage) : {};

    setRenderableItems(content.items.filter(item => !visibilityState[item.id]));
    setActiveIndex(0);
    setIsVisible(true);
    setHasCheckedVisibilityState(true);
  }, [content]);

  useEffect(() => {
    if (!canRotate || isPaused || prefersReducedMotion()) {
      return;
    }

    const intervalId = globalThis.setInterval(() => {
      setActiveIndex(currentIndex => (currentIndex + 1) % renderableItems.length);
    }, rotationIntervalMs);

    return () => globalThis.clearInterval(intervalId);
  }, [canRotate, isPaused, renderableItems.length, rotationIntervalMs]);

  useEffect(() => {
    if (
      !hasCheckedVisibilityState ||
      !activeItem ||
      !isVisible ||
      !isSpotlightCardInVisibleViewport() ||
      viewedItemIdsRef.current.has(activeItem.id)
    ) {
      return;
    }

    viewedItemIdsRef.current.add(activeItem.id);
    sendDocsSpotlightViewEvent(activeItem);
  }, [activeItem, hasCheckedVisibilityState, isVisible]);

  const handleBlur = (event: FocusEvent<HTMLElement>) => {
    const nextFocusedElement = event.relatedTarget;

    if (!(nextFocusedElement instanceof Node) || !event.currentTarget.contains(nextFocusedElement)) {
      setIsPaused(false);
    }
  };

  const recordDisposition = (disposition: DocsSpotlightDisposition) => {
    if (!activeItem) {
      return;
    }

    const storage = getDocsSpotlightBrowserLocalStorage();

    if (!storage) {
      return;
    }

    writeDocsSpotlightVisibilityRecord(storage, activeItem.id, disposition);
  };

  if (!content || !hasCheckedVisibilityState || !activeItem || !isVisible) {
    return null;
  }

  return (
    <aside
      aria-label={content.ariaLabel}
      className={styles.spotlightCard}
      data-testid="docs-spotlight-card"
      onBlurCapture={handleBlur}
      onFocusCapture={() => setIsPaused(true)}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className={styles.spotlightShell}>
        <div className={styles.spotlightHeader}>
          <span className={styles.spotlightKicker}>{content.spotlightLabel}</span>
          <button
            aria-label={content.spotlightDismissLabel}
            className={styles.iconButton}
            onClick={() => {
              sendDocsSpotlightDismissEvent(activeItem);
              recordDisposition('dismissed');
              setIsVisible(false);
            }}
            type="button"
          >
            <XMarkIcon aria-hidden="true" className={styles.icon} />
          </button>
        </div>

        <a
          className={styles.spotlightContent}
          href={createDocsSpotlightTrackingHref(activeItem.href, activeItem.id, locale)}
          onClick={() => {
            sendDocsSpotlightClickEvent(activeItem);
            recordDisposition('viewed');
          }}
        >
          <span className={styles.spotlightImageFrame}>
            <img alt={activeItem.imageAlt} className={styles.spotlightImage} src={activeItem.imageSrc} />
          </span>
          <span className={styles.spotlightCopy}>
            <span className={styles.spotlightTitle}>{activeItem.title}</span>
            <span className={styles.spotlightMeta}>{activeItem.spotlightMeta}</span>
          </span>
          <span className={styles.spotlightCta}>{content.spotlightCtaLabel}</span>
        </a>

        <div className={styles.spotlightFooter}>
          <div aria-hidden="true" className={styles.spotlightIndicators}>
            {renderableItems.map((item, index) => (
              <span
                className={`${styles.spotlightIndicator} ${index === activeIndex ? styles.activeSpotlightIndicator : ''}`}
                key={item.id}
              />
            ))}
          </div>

          <div className={styles.spotlightControls}>
            <button
              aria-label={content.previousLabel}
              className={styles.iconButton}
              onClick={() => {
                setActiveIndex(currentIndex => (currentIndex - 1 + renderableItems.length) % renderableItems.length);
              }}
              type="button"
            >
              <ChevronLeftIcon aria-hidden="true" className={styles.icon} />
            </button>
            <button
              aria-label={content.nextLabel}
              className={styles.iconButton}
              onClick={() => {
                setActiveIndex(currentIndex => (currentIndex + 1) % renderableItems.length);
              }}
              type="button"
            >
              <ChevronRightIcon aria-hidden="true" className={styles.icon} />
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
