'use client';

import cn from 'clsx';
import { useConfig } from 'nextra-theme-docs';
import useLocale from '@/lib/use-locale';

const linkClassName = cn(
  'x:text-xs x:font-medium x:transition',
  'x:text-gray-600 x:dark:text-gray-400',
  'x:hover:text-gray-800 x:dark:hover:text-gray-200',
  'x:contrast-more:text-gray-700 x:contrast-more:dark:text-gray-100',
);

export default function ConfluenceSourceLink() {
  const locale = useLocale('en');
  const { normalizePagesResult } = useConfig();
  const confluenceUrl = normalizePagesResult.activeMetadata?.confluenceUrl;

  if (locale !== 'ko' || !confluenceUrl) return null;

  return (
    <a
      className={linkClassName}
      href={confluenceUrl}
      target="_blank"
      rel="noopener noreferrer"
    >
      View original on Confluence
    </a>
  );
}
