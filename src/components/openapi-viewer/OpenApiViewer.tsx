'use client';

import { useEffect, useState } from 'react';
import { RedocStandalone } from 'redoc';
import type { RedocStandaloneProps } from 'redoc';

/**
 * Props for OpenApiViewer component
 */
interface OpenApiViewerProps {
  /** QueryPie version (e.g., "11.4.1") */
  querypieVersion: string;
  /** API version ("v0.9" or "v2") */
  apiVersion: 'v0.9' | 'v2';
  /** Language code (optional, defaults to "en") */
  lang?: string;
  /** Custom title text to display in Redoc (optional) */
  title?: string;
  /** Custom description text to display in Redoc (optional) */
  description?: string;
}

/**
 * OpenAPI specification type
 */
interface OpenApiSpec {
  openapi?: string;
  swagger?: string;
  info?: {
    title?: string;
    version?: string;
    'x-querypie-version'?: string;
    description?: string;
    'x-logo'?: {
      url?: string;
      altText?: string;
    };
  };
  [key: string]: unknown;
}

/**
 * OpenApiViewer Component
 *
 * Displays OpenAPI specification using Redoc.
 * Loads the specification JSON file from the public directory
 * and renders it using RedocStandalone component.
 *
 * @example
 * ```tsx
 * <OpenApiViewer
 *   querypieVersion="11.4.1"
 *   apiVersion="v2"
 *   lang="en"
 * />
 * ```
 */
export function OpenApiViewer({
  querypieVersion,
  apiVersion,
  lang: _lang = 'en',
  title,
  description,
}: OpenApiViewerProps) {
  const [spec, setSpec] = useState<OpenApiSpec | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const specPath = `/openapi-specification/${querypieVersion}/${apiVersion}.json`;

    // Reset state when version changes
    setLoading(true);
    setError(null);
    setSpec(null);

    fetch(specPath)
      .then((res) => {
        if (!res.ok) {
          throw new Error(
            `Failed to load OpenAPI spec: ${res.status} ${res.statusText}`,
          );
        }
        return res.json();
      })
      .then((data: OpenApiSpec) => {
        // Remove x-logo from spec to prevent Redoc from rendering default logo
        // Also update title and description if title/description props are provided
        const modifiedSpec = { ...data };
        if (!modifiedSpec.info) {
          modifiedSpec.info = {};
        }
        if (modifiedSpec.info['x-logo']) {
          delete modifiedSpec.info['x-logo'];
        }
        // Override title and description with props if provided
        if (title) {
          modifiedSpec.info.title = title;
        }
        if (description) {
          modifiedSpec.info.description = description;
        }
        setSpec(modifiedSpec);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, [querypieVersion, apiVersion, title, description]);

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="mb-4">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Loading OpenAPI specification...
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
        <h3 className="mb-2 text-lg font-semibold text-red-800 dark:text-red-200">
          Error Loading API Specification
        </h3>
        <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        <p className="mt-2 text-xs text-red-600 dark:text-red-400">
          Path: /openapi-specification/{querypieVersion}/{apiVersion}.json
        </p>
      </div>
    );
  }

  // No spec loaded
  if (!spec) {
    return null;
  }

  // Redoc options configuration
  const redocOptions: RedocStandaloneProps['options'] = {
    hideLoading: true,
    sanitize: true,
    showExtensions: true,
    scrollYOffset: 0,
    hideDownloadButton: false,
    disableSearch: false,
    nativeScrollbars: false,
    pathInMiddlePanel: false,
    // Hide default logo using theme option
    theme: {
      logo: {
        maxHeight: '0px',
        maxWidth: '0px',
        gutter: '0px',
      },
    },
  };

  return (
    <div className="openapi-viewer">
      <RedocStandalone spec={spec} options={redocOptions} />
    </div>
  );
}
