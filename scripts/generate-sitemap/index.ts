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

// Configuration
const BASE_URL = 'https://docs.querypie.com';
const CONTENT_DIR = path.join(process.cwd(), 'src', 'content');
const PUBLIC_DIR = path.join(process.cwd(), 'public');
const LANGUAGES = ['en', 'ko', 'ja'] as const;

type Language = typeof LANGUAGES[number];

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
 * Convert file path to URL
 * @param filePath - Path to MDX file
 * @param lang - Language code
 * @returns URL
 */
function filePathToUrl(filePath: string, lang: Language): string {
  // Remove language prefix and file extension
  let urlPath = filePath.replace(`${lang}/`, '').replace('.mdx', '');

  // Handle index.mdx files
  if (urlPath.endsWith('index')) {
    urlPath = urlPath.replace(/index$/, '');
  }

  // Remove trailing slash if present
  if (urlPath.endsWith('/')) {
    urlPath = urlPath.slice(0, -1);
  }

  // Construct full URL
  return `${BASE_URL}/${lang}${urlPath ? '/' + urlPath : ''}`;
}

/**
 * Generate sitemap XML content
 * @param urls - Array of URLs
 * @returns XML content
 */
function generateSitemapXml(urls: string[]): string {
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
  xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';

  for (const url of urls) {
    xml += '  <url>\n';
    xml += `    <loc>${url}</loc>\n`;
    xml += '    <changefreq>weekly</changefreq>\n';
    xml += '    <priority>0.8</priority>\n';
    xml += '  </url>\n';
  }

  xml += '</urlset>';
  return xml;
}

/**
 * Generate sitemap for a specific language
 * @param lang - Language code
 * @returns Array of URLs
 */
function generateLanguageSitemap(lang: Language): string[] {
  const langDir = path.join(CONTENT_DIR, lang);

  if (!fs.existsSync(langDir)) {
    console.warn(`Language directory not found: ${langDir}`);
    return [];
  }

  const mdxFiles = findMdxFiles(langDir, CONTENT_DIR);
  const urls: string[] = [];

  for (const file of mdxFiles) {
    const url = filePathToUrl(file, lang);
    urls.push(url);
  }

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
  
  // Read template file
  let templateContent = fs.readFileSync(templateFile, 'utf8');
  
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
  
  // Write sitemap index file
  const indexFile = path.join(PUBLIC_DIR, 'sitemap.xml');
  fs.writeFileSync(indexFile, xml);
  return indexFile;
}

/**
 * Main function
 */
function main(): void {
  console.log('Generating language-specific sitemap.xml files...');

  // Ensure public directory exists
  if (!fs.existsSync(PUBLIC_DIR)) {
    fs.mkdirSync(PUBLIC_DIR, { recursive: true });
  }

  let totalUrls = 0;

  // Process each language and generate separate sitemap files
  for (const lang of LANGUAGES) {
    const urls = generateLanguageSitemap(lang);
    
    if (urls.length > 0) {
      // Create language-specific directory
      const langDir = path.join(PUBLIC_DIR, lang);
      if (!fs.existsSync(langDir)) {
        fs.mkdirSync(langDir, { recursive: true });
      }
      
      // Generate sitemap XML for this language
      const xml = generateSitemapXml(urls);
      
      // Write to language-specific directory
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
