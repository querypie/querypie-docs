import { DocsSpotlightCard } from '@/components/docs-spotlight-card';
import { getActiveDocsSpotlightContent, resolveDocsSpotlightLocale } from '@/lib/docs-spotlight/content';

type DocsSpotlightSidebarProps = {
  locale?: string;
};

export function DocsSpotlightSidebar({ locale }: DocsSpotlightSidebarProps) {
  const resolvedLocale = resolveDocsSpotlightLocale(locale);
  const content = getActiveDocsSpotlightContent(resolvedLocale);

  return <DocsSpotlightCard content={content} locale={resolvedLocale} />;
}
