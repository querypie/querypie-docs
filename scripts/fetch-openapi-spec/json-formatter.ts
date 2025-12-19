/**
 * JSON formatting utilities
 */

import type { OpenAPISpec, Config } from './types';
import { Logger } from './utils';

/**
 * Default formatting options
 */
const DEFAULT_FORMAT_OPTIONS = {
  indent: 2,
  sortKeys: false, // Keep original key order for better diff readability
};

/**
 * Format JSON content with proper indentation
 */
export function formatJSON(
  json: OpenAPISpec | unknown,
  options: Config['formatOptions'] = DEFAULT_FORMAT_OPTIONS
): string {
  Logger.info('Formatting JSON file...');
  
  try {
    const formatted = JSON.stringify(json, null, options.indent);
    // Add trailing newline to match common file conventions
    return formatted + '\n';
  } catch (error) {
    throw new Error(
      `Failed to format JSON: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Validate JSON structure
 */
export function validateOpenAPISpec(json: unknown): json is OpenAPISpec {
  if (typeof json !== 'object' || json === null) {
    return false;
  }
  
  const spec = json as Record<string, unknown>;
  
  // Check for required OpenAPI fields
  if (!spec.openapi && !spec.swagger) {
    return false;
  }
  
  if (!spec.info || typeof spec.info !== 'object') {
    return false;
  }
  
  return true;
}

