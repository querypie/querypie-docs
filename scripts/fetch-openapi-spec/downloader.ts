/**
 * HTTP downloader for OpenAPI specifications
 */

import type { DownloadOptions, DownloadResult, ApiVersion } from './types';
import { detectApiVersionFromUrl, extractVersionInfo, getApiVersionFilename } from './version-parser';
import { Logger } from './utils';

/**
 * Default timeout for HTTP requests (30 seconds)
 */
const DEFAULT_TIMEOUT = 30000;

/**
 * Download OpenAPI specification from URL
 */
export async function downloadOpenAPISpec(options: DownloadOptions): Promise<DownloadResult> {
  const { url, apiVersion, authToken, timeout = DEFAULT_TIMEOUT } = options;
  
  Logger.info(`Starting OpenAPI Spec download from: ${url}`);
  
  // Detect API version if not provided
  const detectedVersion: ApiVersion = apiVersion || detectApiVersionFromUrl(url);
  Logger.info(`Detected API version: ${detectedVersion}`);
  
  // Prepare fetch options
  const fetchOptions: RequestInit = {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'User-Agent': 'querypie-docs-fetch-openapi-spec/1.0',
    },
    signal: AbortSignal.timeout(timeout),
  };
  
  // Add authentication token if provided
  if (authToken) {
    fetchOptions.headers = {
      ...fetchOptions.headers,
      'Authorization': `Bearer ${authToken}`,
    };
  }
  
  try {
    Logger.info('Downloading JSON file...');
    const response = await fetch(url, fetchOptions);
    
    if (!response.ok) {
      throw new Error(
        `HTTP error! status: ${response.status}, statusText: ${response.statusText}`
      );
    }
    
    const content = await response.text();
    
    // Validate JSON
    let json: unknown;
    try {
      json = JSON.parse(content);
    } catch (parseError) {
      throw new Error(
        `Failed to parse JSON response: ${parseError instanceof Error ? parseError.message : 'Unknown error'}`
      );
    }
    
    // Validate OpenAPI spec structure
    if (typeof json !== 'object' || json === null) {
      throw new Error('Downloaded content is not a valid JSON object');
    }
    
    const spec = json as Record<string, unknown>;
    if (!spec.info || typeof spec.info !== 'object') {
      throw new Error('Downloaded JSON does not contain required "info" field');
    }
    
    // Extract version information
    Logger.info('Extracting version information...');
    const versionInfo = extractVersionInfo(spec as { info?: { 'x-querypie-version'?: string } });
    Logger.info(`Extracted QueryPie version: ${versionInfo.full}`);
    
    return {
      content,
      json: spec as Parameters<typeof extractVersionInfo>[0],
      apiVersion: detectedVersion,
      versionInfo,
    };
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError' || error.message.includes('timeout')) {
        throw new Error(`Request timeout after ${timeout}ms`);
      }
      throw new Error(`Download failed: ${error.message}`);
    }
    throw new Error(`Download failed: ${String(error)}`);
  }
}

