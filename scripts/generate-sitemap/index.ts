/**
 * Sitemap Generator Script
 *
 * This script generates language-specific sitemap.xml files for the QueryPie Manual website.
 * It scans the src/content directory for MDX files and generates URLs according to the specified pattern.
 * Language-specific sitemaps are saved to public/{language}/sitemap.xml.
 * The main public/sitemap.xml is preserved for manual editing.
 */

import * as fs from 'fs';
import * as path from 'path';
import { listGitTrackedFilesInDirectory, type GitTrackedFile } from './git-utils';

// Configuration
const BASE_URL = 'https://docs.querypie.com';
const CONTENT_DIR = path.join(process.cwd(), 'src', 'content');
const PUBLIC_DIR = path.join(process.cwd(), 'public');
const LANGUAGES = ['en', 'ko', 'ja'] as const;

type Language = typeof LANGUAGES[number];

/**
 * Sitemap URL entry type
 */
interface SitemapUrl {
  /** Local file pathname for Git tracking */
  pathname: string;
  /** The URL location */
  loc: string;
  /** Change frequency (daily, weekly, monthly, yearly, never) */
  changefreq: 'daily' | 'weekly' | 'monthly' | 'yearly' | 'never';
  /** Priority value between 0.0 and 1.0 */
  priority: number;
  /** Last modification date (optional) */
  lastmod?: Date;
}


/**
 * Find all MDX files in a directory recursively
 * @param dir - Directory to scan
 * @param baseDir - Base directory for relative path calculation
 * @param result - Array to store results
 * @returns Array of file paths
 */
function findMdxFiles(dir: string, baseDir: string, result: string[] = []): string[] {
  const files = fs.readdirSync(dir);

  for (const file of files) {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);

    if (stat.isDirectory()) {
      findMdxFiles(filePath, baseDir, result);
    } else if (path.extname(file) === '.mdx') {
      // Calculate a relative path from baseDir
      const relativePath = path.relative(baseDir, filePath);
      result.push(relativePath);
    }
  }

  return result;
}

/**
 * Convert file path to SitemapUrl entry
 * @param filePath - Path to MDX file
 * @param lang - Language code
 * @param gitTrackedFiles - Array of Git tracked file information
 * @returns SitemapUrl entry
 */
function filePathToSitemapUrl(filePath: string, lang: Language, gitTrackedFiles: GitTrackedFile[]): SitemapUrl {
  // Remove language prefix and file extension
  let urlPath = filePath.replace(`${lang}/`, '').replace('.mdx', '');

  // Handle index.mdx files
  if (urlPath.endsWith('index')) {
    urlPath = urlPath.replace(/index$/, '');
  }

  // Remove a trailing slash if present
  if (urlPath.endsWith('/')) {
    urlPath = urlPath.slice(0, -1);
  }

  // Construct full URL
  const loc = `${BASE_URL}/${lang}${urlPath ? '/' + urlPath : ''}`;
  
  // Convert absolute filePath to a relative path for Git matching
  const fullFilePath = path.join(CONTENT_DIR, filePath);
  const relativePath = path.relative(CONTENT_DIR, fullFilePath);
  const gitInfo = gitTrackedFiles.find(file => file.pathname === relativePath);
  
  // Determine priority based on the file path
  let priority = 0.7; // Default priority
  const slashCount = (filePath.match(/\//g) || []).length;
  if (filePath.includes('index.mdx') || filePath.endsWith('index.mdx')) {
    priority = 1.0; // Higher priority for index pages
  } else if (slashCount <= 1) {
    priority = 0.9; // High priority for pages with one or fewer slashes
  }
  
  // Set change frequency to weekly for all content
  const changefreq: SitemapUrl['changefreq'] = 'weekly';
  
  return {
    loc,
    changefreq,
    priority,
    pathname: relativePath,
    lastmod: gitInfo?.modified_at
  };
}

/**
 * Generate sitemap XML content from SitemapUrl entries
 * @param urls - Array of SitemapUrl entries
 * @returns XML content
 */
function generateSitemapXml(urls: SitemapUrl[]): string {
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
  xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';

  for (const urlEntry of urls) {
    xml += '  <url>\n';
    xml += `    <loc>${urlEntry.loc}</loc>\n`;
    
    // Add lastmod if available
    if (urlEntry.lastmod) {
      const lastmodDate = urlEntry.lastmod.toISOString();
      xml += `    <lastmod>${lastmodDate}</lastmod>\n`;
    }
    
    xml += `    <changefreq>${urlEntry.changefreq}</changefreq>\n`;
    xml += `    <priority>${urlEntry.priority}</priority>\n`;
    xml += '  </url>\n';
  }

  xml += '</urlset>';
  return xml;
}

/**
 * Generate sitemap for a specific language
 * @param lang - Language code
 * @param gitTrackedFiles - Array of Git tracked file information
 * @returns Array of SitemapUrl entries
 */
function generateLanguageSitemap(lang: Language, gitTrackedFiles: GitTrackedFile[]): SitemapUrl[] {
  const langDir = path.join(CONTENT_DIR, lang);

  if (!fs.existsSync(langDir)) {
    console.warn(`Language directory not found: ${langDir}`);
    return [];
  }

  const mdxFiles = findMdxFiles(langDir, CONTENT_DIR);
  const urls: SitemapUrl[] = [];

  for (const file of mdxFiles) {
    const sitemapUrl = filePathToSitemapUrl(file, lang, gitTrackedFiles);
    urls.push(sitemapUrl);
  }

  // Sort URLs by the last modification date (most recent first)
  urls.sort((a, b) => {
    // If both have lastmod dates, sort by date (newest first)
    if (a.lastmod && b.lastmod) {
      return b.lastmod.getTime() - a.lastmod.getTime();
    }
    // If only one has the lastmod, prioritize it
    if (a.lastmod && !b.lastmod) {
      return -1;
    }
    if (!a.lastmod && b.lastmod) {
      return 1;
    }
    // If neither has lastmod, maintain the original order
    return 0;
  });

  return urls;
}

/**
 * Generate sitemap index file based on template
 * @returns Path to the generated index file
 */
function generateSitemapIndex(): string | undefined {
  const templateFile = path.join(PUBLIC_DIR, '_sitemap.tmpl.xml');
  
  if (!fs.existsSync(templateFile)) {
    console.error(`Template file not found: ${templateFile}`);
    return undefined;
  }
  
  // Read the template file
  const templateContent = fs.readFileSync(templateFile, 'utf8');
  
  // Generate language-specific sitemap entries
  let languageEntries = '';
  for (const lang of LANGUAGES) {
    const sitemapFile = path.join(PUBLIC_DIR, lang, 'sitemap.xml');
    
    if (fs.existsSync(sitemapFile)) {
      languageEntries += '  <sitemap>\n';
      languageEntries += `    <loc>${BASE_URL}/${lang}/sitemap.xml</loc>\n`;
      languageEntries += '  </sitemap>\n';
    }
  }
  
  // Replace placeholder with language entries
  const xml = templateContent.replace('<!-- LANGUAGE_SITEMAPS_PLACEHOLDER -->', languageEntries);
  
  // Write a sitemap index file
  const indexFile = path.join(PUBLIC_DIR, 'sitemap.xml');
  fs.writeFileSync(indexFile, xml);
  return indexFile;
}

/**
 * Main function
 */
function main(): void {
  console.log('Generating language-specific sitemap.xml files...');

  // Get Git tracked files information
  console.log('Getting Git tracked files information...');
  const gitTrackedFiles = listGitTrackedFilesInDirectory('src/content');
  console.log(`Found ${gitTrackedFiles.length} Git tracked files`);

  // Ensure the public directory exists
  if (!fs.existsSync(PUBLIC_DIR)) {
    fs.mkdirSync(PUBLIC_DIR, { recursive: true });
  }

  let totalUrls = 0;

  // Process each language and generate separate sitemap files
  for (const lang of LANGUAGES) {
    const urls = generateLanguageSitemap(lang, gitTrackedFiles);
    
    if (urls.length > 0) {
      // Create a language-specific directory
      const langDir = path.join(PUBLIC_DIR, lang);
      if (!fs.existsSync(langDir)) {
        fs.mkdirSync(langDir, { recursive: true });
      }
      
      // Generate sitemap XML for this language
      const xml = generateSitemapXml(urls);
      
      // Write to the language-specific directory
      const outputFile = path.join(langDir, 'sitemap.xml');
      fs.writeFileSync(outputFile, xml);
      const relativePath = path.relative(process.cwd(), outputFile);
      console.log(`${lang}: ${urls.length} URLs -> ${relativePath}`);
      totalUrls += urls.length;
    }
  }

  // Generate sitemap index file
  const indexFile = generateSitemapIndex();
  const relativeIndexPath = indexFile ? path.relative(process.cwd(), indexFile) : 'Failed to generate';

  console.log(`\nTotal: ${totalUrls} URLs`);
  console.log(`Sitemap index: ${relativeIndexPath}`);
}

// Run the script
main();
