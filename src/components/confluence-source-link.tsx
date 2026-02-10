'use client';

import { useConfig } from 'nextra-theme-docs';
import useLocale from '@/lib/use-locale';

const styles = `
  .confluence-source-link {
    padding: 8px 0 16px 0;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 16px;
  }

  .dark .confluence-source-link {
    border-bottom-color: #374151;
  }

  .confluence-source-link a {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: #6b7280;
    text-decoration: none;
    transition: color 0.2s ease;
  }

  .confluence-source-link a:hover {
    color: #2563eb;
  }

  .dark .confluence-source-link a {
    color: #9ca3af;
  }

  .dark .confluence-source-link a:hover {
    color: #60a5fa;
  }
`;

export default function ConfluenceSourceLink() {
  const locale = useLocale('en');
  const { normalizePagesResult } = useConfig();
  const confluenceUrl = normalizePagesResult.activeMetadata?.confluenceUrl;

  if (locale !== 'ko' || !confluenceUrl) return null;

  return (
    <>
      <style>{styles}</style>
      <div className="confluence-source-link">
        <a href={confluenceUrl} target="_blank" rel="noopener noreferrer">
          Confluence 원문 ↗
        </a>
      </div>
    </>
  );
}
