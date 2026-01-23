/**
 * Test script to demonstrate git-utils.ts usage
 * Lists all Git-tracked files in src/content/ko directory
 */

import { execSync } from 'child_process';
import { listGitTrackedFilesInDirectory } from './git-utils';

function main(): void {
  console.log('Testing git-utils.ts with src/content/ko directory...');
  
  try {
    // Debug: Check what the git command returns
    
    const command = `git log --pretty=format:"%H|%cd" --date=iso --name-only -- "src/content/ko/"`;
    console.log('Git command:', command);
    const result = execSync(command, { encoding: 'utf8', cwd: process.cwd() });
    console.log('Git result (first 500 chars):', result.substring(0, 500));
    console.log('---');
    
    const files = listGitTrackedFilesInDirectory('src/content/ko');
    
    console.log(`\nFound ${files.length} Git-tracked files in src/content/ko:`);
    console.log('='.repeat(60));
    
    // Show only the first 10 files
    files.slice(0, 10).forEach((file, index) => {
      console.log(`${index + 1}. ${file.pathname}`);
      console.log(`   Commit: ${file.commit_hash}`);
      console.log(`   Modified: ${file.modified_at.toISOString()}`);
      console.log('');
    });
    
    if (files.length > 10) {
      console.log(`... and ${files.length - 10} more files`);
    }
    
    console.log(`Total: ${files.length} files`);
  } catch (error) {
    console.error('Error:', error instanceof Error ? error.message : 'Unknown error');
  }
}

// Run the test
main();
