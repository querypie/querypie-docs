/**
 * Version parsing utilities
 */

import type { ApiVersion, VersionInfo, OpenAPISpec } from './types';
import { Logger } from './utils';

/**
 * Detect API version from URL
 */
export function detectApiVersionFromUrl(url: string): ApiVersion {
  const lowerUrl = url.toLowerCase();
  
  // Check for v2 indicators
  if (lowerUrl.includes('/external-v2') || lowerUrl.includes('/v2') || lowerUrl.includes('/specification/external-v2')) {
    return 'v2';
  }
  
  // Default to v0.9
  if (lowerUrl.includes('/external') || lowerUrl.includes('/specification/external')) {
    return 'v0.9';
  }
  
  // If no clear indicator, default to v0.9
  Logger.warn(`Could not detect API version from URL, defaulting to v0.9: ${url}`);
  return 'v0.9';
}

/**
 * Extract version information from OpenAPI spec
 */
export function extractVersionInfo(spec: OpenAPISpec): VersionInfo {
  const versionString = spec.info?.['x-querypie-version'];
  
  if (!versionString || typeof versionString !== 'string') {
    throw new Error(
      'Missing or invalid x-querypie-version field in OpenAPI spec. ' +
      'Expected format: {major}.{minor}.{patch}-{commit-hash}'
    );
  }

  // Parse version string: "11.4.1-eee1211" -> { major: "11", minor: "4", patch: "1", commit: "eee1211" }
  const versionMatch = versionString.match(/^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$/);
  
  if (!versionMatch) {
    throw new Error(
      `Invalid version format: ${versionString}. ` +
      'Expected format: {major}.{minor}.{patch}-{commit-hash}'
    );
  }

  const [, major, minor, patch, commit] = versionMatch;
  const directory = `${major}.${minor}.${patch}`;

  return {
    full: versionString,
    directory,
    commit: commit || undefined,
  };
}

/**
 * Get filename for API version
 */
export function getApiVersionFilename(apiVersion: ApiVersion): string {
  return `${apiVersion}.json`;
}

