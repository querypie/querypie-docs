/**
 * File management utilities
 */

import * as path from 'path';
import * as fs from 'fs';
import type { SaveOptions, Config } from './types';
import { Logger, ensureDirectory, fileExists, calculateHash, getRelativePath } from './utils';
import { getApiVersionFilename } from './version-parser';

/**
 * Default configuration
 */
const DEFAULT_CONFIG: Config = {
  baseDir: path.join(process.cwd(), 'public', 'openapi-specification'),
  defaultTimeout: 30000,
  formatOptions: {
    indent: 2,
    sortKeys: false,
  },
};

/**
 * Get full file path for OpenAPI spec
 */
export function getSpecFilePath(versionDirectory: string, apiVersion: string): string {
  const config = DEFAULT_CONFIG;
  const filename = getApiVersionFilename(apiVersion as 'v0.9' | 'v2');
  return path.join(config.baseDir, versionDirectory, filename);
}

/**
 * Save formatted JSON to file
 */
export function saveSpecFile(options: SaveOptions): string {
  const { versionDirectory, apiVersion, content, overwrite = true } = options;
  const config = DEFAULT_CONFIG;
  
  // Create version directory
  const versionDir = path.join(config.baseDir, versionDirectory);
  ensureDirectory(versionDir);
  
  // Get file path
  const filename = getApiVersionFilename(apiVersion);
  const filePath = path.join(versionDir, filename);
  const relativePath = getRelativePath(filePath);
  
  // Check if file exists
  if (fileExists(filePath)) {
    if (!overwrite) {
      throw new Error(`File already exists and overwrite is disabled: ${relativePath}`);
    }
    
    // Check if content has changed
    const existingContent = fs.readFileSync(filePath, 'utf-8');
    const existingHash = calculateHash(existingContent);
    const newHash = calculateHash(content);
    
    if (existingHash === newHash) {
      Logger.warn(`File content unchanged, skipping save: ${relativePath}`);
      return filePath;
    }
    
    Logger.warn(`Overwriting existing file: ${relativePath}`);
  }
  
  // Validate JSON before saving
  try {
    JSON.parse(content);
  } catch (error) {
    throw new Error(
      `Invalid JSON content cannot be saved: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
  
  // Write file
  try {
    fs.writeFileSync(filePath, content, 'utf-8');
    Logger.info(`Saved file: ${relativePath}`);
    return filePath;
  } catch (error) {
    throw new Error(
      `Failed to write file: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Get configuration
 */
export function getConfig(): Config {
  return DEFAULT_CONFIG;
}

