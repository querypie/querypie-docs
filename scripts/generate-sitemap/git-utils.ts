/**
 * Git Utilities Library
 * 
 * This library provides utilities for extracting Git commit information
 * for files in a specified directory.
 */

import { execSync } from 'child_process';

/**
 * Git tracked file information
 */
export interface GitTrackedFile {
  /** File path relative to the Git repository */
  pathname: string;
  /** Git commit hash of the last commit that modified this file */
  commit_hash: string;
  /** Date when the file was last modified (from Git commit) */
  modified_at: Date;
}


/**
 * List all Git-tracked files in a directory with their commit information
 * 
 * @param directoryPath - Path to the directory relative to the Git repository
 * @returns Array of Git tracked file information
 */
export function listGitTrackedFilesInDirectory(directoryPath: string): GitTrackedFile[] {
  try {
    const cwd = process.cwd();
    
    // Single git log command to get all commit information for files in the directory
    const command = `git log --pretty=format:"%H|%cd" --date=iso --name-only -- "${directoryPath}/"`;
    const result = execSync(command, { encoding: 'utf8', cwd });
    
    const fileInfoMap = new Map<string, GitTrackedFile>();
    let currentCommit: { hash: string; date: string } | null = null;
    
    result.split('\n').forEach(line => {
      const trimmedLine = line.trim();
      if (/^[0-9a-f]{40}\|/.test(trimmedLine)) {
        const [hash, date] = trimmedLine.split('|');
        currentCommit = { hash, date };
      } else if (trimmedLine && (trimmedLine.startsWith(directoryPath + '/') || trimmedLine === directoryPath)) {
        if (currentCommit) {
          // Only set if we don't already have info for this file (first occurrence is most recent)
          if (!fileInfoMap.has(trimmedLine)) {
            // Create a relative pathname from the specified directory
            const relativePath = trimmedLine.startsWith(directoryPath + '/') 
              ? trimmedLine.substring(directoryPath.length + 1)
              : trimmedLine === directoryPath 
                ? '.'
                : trimmedLine;
            
            fileInfoMap.set(trimmedLine, {
              pathname: relativePath,
              commit_hash: currentCommit.hash,
              modified_at: new Date(currentCommit.date)
            });
          }
        }
      }
    });
    
    return Array.from(fileInfoMap.values());
  } catch (error) {
    console.warn('Failed to get Git tracked files info:', error instanceof Error ? error.message : 'Unknown error');
    return [];
  }
}
