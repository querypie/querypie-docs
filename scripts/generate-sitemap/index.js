/* eslint-disable @typescript-eslint/no-require-imports */

/**
 * Sitemap Generator Script
 *
 * This script generates a sitemap.xml file for the QueryPie Manual website.
 * It scans the src/content directory for MDX files and generates URLs according to the specified pattern.
 * The sitemap is saved to public/sitemap.xml.
 */

const fs = require('fs');
const path = require('path');

// Configuration
const BASE_URL = 'https://docs.querypie.io';
const CONTENT_DIR = path.join(process.cwd(), 'src', 'content');
const OUTPUT_FILE = path.join(process.cwd(), 'public', 'sitemap.xml');
const LANGUAGES = ['en', 'ko', 'ja'];

/**
 * Find all MDX files in a directory recursively
 * @param {string} dir - Directory to scan
 * @param {string} baseDir - Base directory for relative path calculation
 * @param {Array} result - Array to store results
 * @returns {Array} - Array of file paths
 */
function findMdxFiles(dir, baseDir, result = []) {
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
 * @param {string} filePath - Path to MDX file
 * @param {string} lang - Language code
 * @returns {string} - URL
 */
function filePathToUrl(filePath, lang) {
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
 * @param {Array} urls - Array of URLs
 * @returns {string} - XML content
 */
function generateSitemapXml(urls) {
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
 * Main function
 */
function main() {
  console.log('Generating sitemap.xml...');

  const urls = [];

  // Process each language
  for (const lang of LANGUAGES) {
    const langDir = path.join(CONTENT_DIR, lang);

    if (!fs.existsSync(langDir)) {
      console.warn(`Language directory not found: ${langDir}`);
      continue;
    }

    console.log(`Processing language: ${lang}`);
    const mdxFiles = findMdxFiles(langDir, CONTENT_DIR);

    for (const file of mdxFiles) {
      const url = filePathToUrl(file, lang);
      urls.push(url);
      console.log(`Added URL: ${url}`);
    }
  }

  // Generate sitemap XML
  const xml = generateSitemapXml(urls);

  // Write to file
  fs.writeFileSync(OUTPUT_FILE, xml);
  console.log(`Sitemap generated at: ${OUTPUT_FILE}`);
  console.log(`Total URLs: ${urls.length}`);
}

// Run the script
main();
