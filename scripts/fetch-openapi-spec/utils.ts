/**
 * Utility functions for fetch-openapi-spec
 */

import * as path from 'path';
import * as fs from 'fs';

/**
 * Log levels
 */
export enum LogLevel {
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

/**
 * Logger utility
 */
export class Logger {
  /**
   * Log a message with specified level
   */
  static log(level: LogLevel, message: string, ...args: unknown[]): void {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level}]`;
    const formattedMessage = args.length > 0 
      ? `${prefix} ${message} ${args.map(arg => JSON.stringify(arg)).join(' ')}`
      : `${prefix} ${message}`;
    
    console.log(formattedMessage);
  }

  /**
   * Log info message
   */
  static info(message: string, ...args: unknown[]): void {
    this.log(LogLevel.INFO, message, ...args);
  }

  /**
   * Log warning message
   */
  static warn(message: string, ...args: unknown[]): void {
    this.log(LogLevel.WARN, message, ...args);
  }

  /**
   * Log error message
   */
  static error(message: string, ...args: unknown[]): void {
    this.log(LogLevel.ERROR, message, ...args);
  }
}

/**
 * Ensure directory exists, create if not
 */
export function ensureDirectory(dirPath: string): void {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    Logger.info(`Created directory: ${dirPath}`);
  }
}

/**
 * Calculate file hash (simple implementation)
 */
export function calculateHash(content: string): string {
  // Simple hash function for change detection
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(16);
}

/**
 * Check if file exists
 */
export function fileExists(filePath: string): boolean {
  return fs.existsSync(filePath);
}

/**
 * Read file content
 */
export function readFile(filePath: string): string {
  return fs.readFileSync(filePath, 'utf-8');
}

/**
 * Get relative path from project root
 */
export function getRelativePath(filePath: string): string {
  return path.relative(process.cwd(), filePath);
}

