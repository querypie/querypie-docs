/**
 * Type definitions for fetch-openapi-spec
 */

/**
 * API version type
 */
export type ApiVersion = 'v0.9' | 'v2';

/**
 * OpenAPI Specification info object with QueryPie extension
 */
export interface OpenAPIInfo {
  title?: string;
  version?: string;
  'x-querypie-version'?: string;
  [key: string]: unknown;
}

/**
 * OpenAPI Specification structure
 */
export interface OpenAPISpec {
  openapi?: string;
  info?: OpenAPIInfo;
  [key: string]: unknown;
}

/**
 * Parsed version information
 */
export interface VersionInfo {
  /** Full version string (e.g., "11.4.1-eee1211") */
  full: string;
  /** Major.minor.patch version (e.g., "11.4.1") */
  directory: string;
  /** Commit hash (e.g., "eee1211") */
  commit?: string;
}

/**
 * Download options
 */
export interface DownloadOptions {
  /** URL to download from */
  url: string;
  /** API version (auto-detected if not provided) */
  apiVersion?: ApiVersion;
  /** Authentication token (optional) */
  authToken?: string;
  /** Request timeout in milliseconds */
  timeout?: number;
}

/**
 * Download result
 */
export interface DownloadResult {
  /** Downloaded JSON content */
  content: string;
  /** Parsed JSON object */
  json: OpenAPISpec;
  /** Detected API version */
  apiVersion: ApiVersion;
  /** Extracted version information */
  versionInfo: VersionInfo;
}

/**
 * File save options
 */
export interface SaveOptions {
  /** QueryPie version directory name (e.g., "11.4.1") */
  versionDirectory: string;
  /** API version (v0.9 or v2) */
  apiVersion: ApiVersion;
  /** Formatted JSON content */
  content: string;
  /** Whether to overwrite existing file */
  overwrite?: boolean;
}

/**
 * Program configuration
 */
export interface Config {
  /** Base directory for OpenAPI specs */
  baseDir: string;
  /** Default timeout for HTTP requests */
  defaultTimeout: number;
  /** JSON formatting options */
  formatOptions: {
    indent: number;
    sortKeys: boolean;
  };
}

