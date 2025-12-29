import { Metadata } from 'next';
import { OpenApiViewer } from '@/components/openapi-viewer';
import { notFound } from 'next/navigation';
import fs from 'fs';
import path from 'path';
import { createModuleLogger } from '@/lib/logger';

// Create logger for API reference page
const logger = createModuleLogger('api-reference');

/**
 * Generate static params for all available API reference pages
 * Scans the public/openapi-specification directory to find all versions
 */
export async function generateStaticParams() {
  const locales = ['en', 'ja', 'ko'];
  const specBasePath = path.join(process.cwd(), 'public', 'openapi-specification');
  const paramsList: {
    lang: string;
    acpVersion: string;
    apiVersion: string;
  }[] = [];

  // Debug logging (only in non-production environments)
  logger.debug('generateStaticParams called', {
    specBasePath,
    cwd: process.cwd(),
    specBasePathExists: fs.existsSync(specBasePath),
  });

  // Check if the base directory exists
  if (!fs.existsSync(specBasePath)) {
    logger.warn('specBasePath does not exist', { specBasePath });
    return paramsList;
  }

  // Scan for version directories (e.g., 11.4.1)
  const versionDirs = fs
    .readdirSync(specBasePath, { withFileTypes: true })
    .filter((dirent) => dirent.isDirectory())
    .map((dirent) => dirent.name);

  logger.debug('Found version directories', { versionDirs });

  // For each version directory, find available API versions
  for (const acpVersion of versionDirs) {
    const versionPath = path.join(specBasePath, acpVersion);
    const files = fs.readdirSync(versionPath);

    logger.debug(`Scanning ${acpVersion}`, { files });

    // Find API version files (v2.json, v0.9.json)
    const apiVersions = files
      .filter((file) => file.endsWith('.json'))
      .map((file) => path.parse(file).name) // Remove .json extension
      .filter((name) => name === 'v2' || name === 'v0.9'); // Only valid API versions

    logger.debug(`Valid API versions for ${acpVersion}`, { apiVersions });

    // Generate params for each combination of locale, acpVersion, and apiVersion
    for (const lang of locales) {
      for (const apiVersion of apiVersions) {
        const param = {
          lang,
          acpVersion,
          apiVersion,
        };
        paramsList.push(param);
        logger.debug('Generated param', param);
      }
    }
  }

  logger.info('Total params generated', { count: paramsList.length });
  return paramsList;
}

/**
 * Get localized text for API reference page
 */
function getLocalizedText(
  lang: string,
  apiVersion: string,
  acpVersion: string,
): {
  title: string;
  description: string;
} {
  const upperApiVersion = apiVersion.toUpperCase();

  switch (lang) {
    case 'ko':
      return {
        title: `QueryPie ACP External API 레퍼런스 - ${upperApiVersion}`,
        description: `이 페이지는 QueryPie ACP External API ${upperApiVersion} (버전 ${acpVersion})의 전체 OpenAPI 명세서를 제공합니다.`,
      };
    case 'ja':
      return {
        title: `QueryPie ACP External APIリファレンス - ${upperApiVersion}`,
        description: `このページは、QueryPie ACP External API ${upperApiVersion} (バージョン ${acpVersion}) の完全なOpenAPI仕様書を提供します。`,
      };
    case 'en':
    default:
      return {
        title: `QueryPie ACP External API Reference - ${upperApiVersion}`,
        description: `This page provides the complete OpenAPI specification for QueryPie ACP External API ${upperApiVersion} (Version ${acpVersion}).`,
      };
  }
}

/**
 * Type for API reference page params
 * Next.js uses exact segment names as keys, so [acpVersion] becomes 'acpVersion'
 */
type ApiReferenceParams = {
  lang: string;
  acpVersion: string;
  apiVersion: string;
};

/**
 * Generate metadata for the API reference page
 */
export async function generateMetadata(props: {
  params: Promise<ApiReferenceParams>;
}): Promise<Metadata> {
  const params = await props.params;
  const lang = params.lang;
  const acpVersion = params.acpVersion;
  const apiVersion = params.apiVersion;

  // Validate API version
  if (apiVersion !== 'v2' && apiVersion !== 'v0.9') {
    return {
      title: 'API Reference Not Found',
      description: 'The requested API version does not exist.',
    };
  }

  const { title, description } = getLocalizedText(lang, apiVersion, acpVersion);

  return {
    title,
    description,
  };
}

/**
 * API Reference Page Component
 *
 * Displays the OpenAPI specification for a specific QueryPie ACP External API version.
 * Replaces the functionality of the v2.mdx file.
 */
export default async function ApiReferencePage(props: {
  params: Promise<ApiReferenceParams>;
}) {
  const params = await props.params;
  
  // Debug logging (only in non-production environments)
  logger.debug('Component rendered', {
    paramsKeys: Object.keys(params),
    params: params,
  });
  
  // Next.js uses exact segment names as keys, so [acpVersion] becomes 'acpVersion'
  const lang = params.lang;
  const acpVersion = params.acpVersion;
  const apiVersion = params.apiVersion;
  
  logger.debug('Extracted values', { lang, acpVersion, apiVersion });
  logger.debug('Request URL', { url: `/api-reference/${acpVersion}/${apiVersion}` });
  
  // Validate that we got the values
  if (!acpVersion || !apiVersion) {
    logger.error('Missing required params', { acpVersion, apiVersion });
    notFound();
  }

  // Validate API version
  if (apiVersion !== 'v2' && apiVersion !== 'v0.9') {
    logger.error('Invalid API version', { apiVersion });
    notFound();
  }

  const { title, description } = getLocalizedText(lang, apiVersion, acpVersion);

  return (
    <div className="api-reference-page">
      <OpenApiViewer
        querypieVersion={acpVersion}
        apiVersion={apiVersion as 'v2' | 'v0.9'}
        lang={lang}
        title={title}
        description={description}
      />
    </div>
  );
}
