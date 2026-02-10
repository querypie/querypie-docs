'use client';

import cn from 'clsx';
import { Anchor } from 'nextra/components';
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
    <Anchor
      className={linkClassName}
      href={confluenceUrl}
    >
      View original on Confluence
    </Anchor>
  );
}
