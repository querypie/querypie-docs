/* eslint-disable @typescript-eslint/no-require-imports */

/**
 * Sitemap Generator Script
 *
 * This script generates language-specific sitemap.xml files for the QueryPie Manual website.
 * It scans the src/content directory for MDX files and generates URLs according to the specified pattern.
 * Language-specific sitemaps are saved to public/{language}/sitemap.xml.
 * The main public/sitemap.xml is preserved for manual editing.
 */

const fs = require('fs');
const path = require('path');

// Configuration
const BASE_URL = 'https://docs.querypie.io';
const CONTENT_DIR = path.join(process.cwd(), 'src', 'content');
const PUBLIC_DIR = path.join(process.cwd(), 'public');
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
 * Generate sitemap for a specific language
 * @param {string} lang - Language code
 * @returns {Array} - Array of URLs
 */
function generateLanguageSitemap(lang) {
  const langDir = path.join(CONTENT_DIR, lang);

  if (!fs.existsSync(langDir)) {
    console.warn(`Language directory not found: ${langDir}`);
    return [];
  }

  console.log(`Processing language: ${lang}`);
  const mdxFiles = findMdxFiles(langDir, CONTENT_DIR);
  const urls = [];

  for (const file of mdxFiles) {
    const url = filePathToUrl(file, lang);
    urls.push(url);
    console.log(`Added URL: ${url}`);
  }

  return urls;
}

/**
 * Main function
 */
function main() {
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
        console.log(`Created directory: ${langDir}`);
      }
      
      // Generate sitemap XML for this language
      const xml = generateSitemapXml(urls);
      
      // Write to language-specific directory
      const outputFile = path.join(langDir, 'sitemap.xml');
      fs.writeFileSync(outputFile, xml);
      console.log(`Sitemap generated at: ${outputFile}`);
      console.log(`Total URLs for ${lang}: ${urls.length}`);
      totalUrls += urls.length;
    }
  }

  // Generate sitemap index file
  generateSitemapIndex();

  console.log(`\nAll sitemaps generated successfully!`);
  console.log(`Total URLs across all languages: ${totalUrls}`);
  console.log(`Language-specific sitemaps saved to public/{language}/sitemap.xml`);
  console.log(`Sitemap index updated at public/sitemap.xml`);
}

/**
 * Generate sitemap index file based on template
 */
function generateSitemapIndex() {
  const templateFile = path.join(PUBLIC_DIR, '_sitemap.tmpl.xml');
  
  if (!fs.existsSync(templateFile)) {
    console.error(`Template file not found: ${templateFile}`);
    return;
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
  console.log(`Sitemap index generated at: ${indexFile}`);
}

// Run the script
main();
