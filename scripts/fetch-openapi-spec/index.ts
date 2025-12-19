#!/usr/bin/env node

/**
 * Main entry point for fetch-openapi-spec
 * 
 * Downloads OpenAPI specification from QueryPie instance and saves it to the repository.
 * 
 * Usage:
 *   npm run fetch-openapi-spec -- <url>
 *   npm run fetch-openapi-spec -- https://internal.dev.querypie.io/api/docs/specification/external-v2
 * 
 * Options:
 *   --api-version <version>  Specify API version (v0.9 or v2). Auto-detected from URL if not provided.
 *   --auth-token <token>      Authentication token for protected endpoints.
 *   --timeout <ms>            Request timeout in milliseconds (default: 30000).
 *   --no-overwrite           Do not overwrite existing files.
 *   --help                   Show this help message.
 */

import * as process from 'process';
import type { DownloadOptions } from './types';
import { downloadOpenAPISpec } from './downloader';
import { formatJSON } from './json-formatter';
import { saveSpecFile } from './file-manager';
import { Logger } from './utils';
import { validateOpenAPISpec } from './json-formatter';

/**
 * Parse command line arguments
 */
function parseArgs(): {
  url?: string;
  apiVersion?: 'v0.9' | 'v2';
  authToken?: string;
  timeout?: number;
  overwrite: boolean;
  help: boolean;
} {
  const args = process.argv.slice(2);
  const result: {
    url?: string;
    apiVersion?: 'v0.9' | 'v2';
    authToken?: string;
    timeout?: number;
    overwrite: boolean;
    help: boolean;
  } = {
    overwrite: true,
    help: false,
  };
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    if (arg === '--help' || arg === '-h') {
      result.help = true;
      return result;
    }
    
    if (arg === '--api-version' && i + 1 < args.length) {
      const version = args[++i];
      if (version === 'v0.9' || version === 'v2') {
        result.apiVersion = version;
      } else {
        throw new Error(`Invalid API version: ${version}. Must be 'v0.9' or 'v2'`);
      }
    } else if (arg === '--auth-token' && i + 1 < args.length) {
      result.authToken = args[++i];
    } else if (arg === '--timeout' && i + 1 < args.length) {
      const timeout = parseInt(args[++i], 10);
      if (isNaN(timeout) || timeout <= 0) {
        throw new Error(`Invalid timeout value: ${args[i]}. Must be a positive number`);
      }
      result.timeout = timeout;
    } else if (arg === '--no-overwrite') {
      result.overwrite = false;
    } else if (!arg.startsWith('--') && !result.url) {
      result.url = arg;
    }
  }
  
  return result;
}

/**
 * Print help message
 */
function printHelp(): void {
  console.log(`
Usage: npm run fetch-openapi-spec -- <url> [options]

Downloads OpenAPI specification from QueryPie instance and saves it to the repository.

Arguments:
  <url>                    URL to download OpenAPI spec from
                           Example: https://internal.dev.querypie.io/api/docs/specification/external-v2

Options:
  --api-version <version>   Specify API version (v0.9 or v2). Auto-detected from URL if not provided.
  --auth-token <token>      Authentication token for protected endpoints.
  --timeout <ms>            Request timeout in milliseconds (default: 30000).
  --no-overwrite           Do not overwrite existing files.
  --help, -h               Show this help message.

Examples:
  # Download V2 API spec (auto-detect version from URL)
  npm run fetch-openapi-spec -- https://internal.dev.querypie.io/api/docs/specification/external-v2

  # Download V0.9 API spec
  npm run fetch-openapi-spec -- https://internal.dev.querypie.io/api/docs/specification/external

  # Download with explicit API version
  npm run fetch-openapi-spec -- https://example.com/api/spec --api-version v2

  # Download with authentication
  npm run fetch-openapi-spec -- https://example.com/api/spec --auth-token <token>
`);
}

/**
 * Main function
 */
async function main(): Promise<void> {
  try {
    const args = parseArgs();
    
    if (args.help) {
      printHelp();
      process.exit(0);
    }
    
    if (!args.url) {
      Logger.error('URL argument is required');
      printHelp();
      process.exit(1);
    }
    
    // Download OpenAPI spec
    const downloadOptions: DownloadOptions = {
      url: args.url,
      apiVersion: args.apiVersion,
      authToken: args.authToken,
      timeout: args.timeout,
    };
    
    const result = await downloadOpenAPISpec(downloadOptions);
    
    // Validate OpenAPI spec structure
    if (!validateOpenAPISpec(result.json)) {
      throw new Error('Downloaded content is not a valid OpenAPI specification');
    }
    
    // Format JSON
    const formattedContent = formatJSON(result.json);
    
    // Save file
    const filePath = saveSpecFile({
      versionDirectory: result.versionInfo.directory,
      apiVersion: result.apiVersion,
      content: formattedContent,
      overwrite: args.overwrite,
    });
    
    Logger.info('Download completed successfully!');
    Logger.info(`File saved to: ${filePath}`);
    
    process.exit(0);
  } catch (error) {
    Logger.error(
      error instanceof Error ? error.message : String(error)
    );
    
    if (error instanceof Error && error.stack) {
      Logger.error(`Stack trace: ${error.stack}`);
    }
    
    process.exit(1);
  }
}

// Run main function
main();

