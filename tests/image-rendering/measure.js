#!/usr/bin/env node

/**
 * Image Rendering Measurement Tool
 *
 * Measures rendered image sizes on a web page using Playwright.
 *
 * Usage:
 *   node measure.js <url> [options]
 *
 * Options:
 *   --output, -o    Output file path (default: stdout)
 *   --format, -f    Output format: json, markdown, table (default: table)
 *   --viewport, -v  Viewport size WxH (default: 1920x1080)
 *   --headless      Run in headless mode (default: false)
 *   --min-size      Minimum image size to include (default: 50)
 *
 * Examples:
 *   node measure.js https://example.com/page
 *   node measure.js https://example.com/page -f markdown -o report.md
 *   node measure.js https://example.com/page -f json -o result.json
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

function parseArgs(args) {
  const options = {
    url: null,
    output: null,
    format: 'table',
    viewport: { width: 1920, height: 1080 },
    headless: false,
    minSize: 50,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg.startsWith('http://') || arg.startsWith('https://')) {
      options.url = arg;
    } else if (arg === '--output' || arg === '-o') {
      options.output = args[++i];
    } else if (arg === '--format' || arg === '-f') {
      options.format = args[++i];
    } else if (arg === '--viewport' || arg === '-v') {
      const [width, height] = args[++i].split('x').map(Number);
      options.viewport = { width, height };
    } else if (arg === '--headless') {
      options.headless = true;
    } else if (arg === '--min-size') {
      options.minSize = parseInt(args[++i], 10);
    }
  }

  return options;
}

async function measureImages(url, options) {
  const browser = await chromium.launch({
    headless: options.headless,
    args: ['--window-size=1920,1080'],
  });

  const context = await browser.newContext({
    viewport: options.viewport,
  });

  const page = await context.newPage();

  console.error(`Loading: ${url}`);
  await page.goto(url, { waitUntil: 'load', timeout: 60000 });

  // Wait for images to load
  await page.waitForTimeout(5000);

  const images = await page.evaluate((minSize) => {
    const imgs = document.querySelectorAll('img');
    return Array.from(imgs)
      .map((img, index) => {
        const rect = img.getBoundingClientRect();
        const src = img.src || img.getAttribute('src') || '';

        // Extract filename - try multiple sources
        let filename = '';

        // 1. Try data-filename attribute (Confluence)
        filename = img.getAttribute('data-filename') || '';

        // 2. Try alt attribute if it looks like a filename
        if (!filename || filename === 'cdn') {
          const alt = img.alt || '';
          if (alt && (alt.includes('.png') || alt.includes('.jpg') || alt.includes('.gif') || alt.includes('.webp'))) {
            filename = alt;
          }
        }

        // 3. Try to extract from URL pathname
        if (!filename || filename === 'cdn') {
          try {
            const urlObj = new URL(src, window.location.origin);
            const pathname = urlObj.pathname;
            const pathFilename = decodeURIComponent(pathname.split('/').pop() || '');
            if (pathFilename && pathFilename !== 'cdn' && pathFilename.length > 0) {
              filename = pathFilename;
            }
          } catch {
            // ignore
          }
        }

        // 4. Try title attribute
        if (!filename || filename === 'cdn') {
          filename = img.title || '';
        }

        // 5. Fallback to index-based name
        if (!filename || filename === 'cdn') {
          filename = `image-${index + 1}`;
        }

        return {
          filename,
          src: src.substring(0, 150),
          rendered: {
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          },
          natural: {
            width: img.naturalWidth,
            height: img.naturalHeight,
          },
          attributes: {
            width: img.getAttribute('width'),
            height: img.getAttribute('height'),
            style: img.style.cssText || null,
          },
        };
      })
      .filter(
        (img) =>
          img.rendered.width >= minSize && img.rendered.height >= minSize
      );
  }, options.minSize);

  await browser.close();

  return {
    url,
    timestamp: new Date().toISOString(),
    viewport: options.viewport,
    imageCount: images.length,
    images,
  };
}

function formatTable(result) {
  const lines = [];
  lines.push(`URL: ${result.url}`);
  lines.push(`Timestamp: ${result.timestamp}`);
  lines.push(`Viewport: ${result.viewport.width}x${result.viewport.height}`);
  lines.push(`Images: ${result.imageCount}`);
  lines.push('');
  lines.push(
    '| # | Filename | Rendered (WxH) | Natural (WxH) | HTML Width |'
  );
  lines.push(
    '|---|----------|----------------|---------------|------------|'
  );

  result.images.forEach((img, i) => {
    const rendered = `${img.rendered.width} x ${img.rendered.height}`;
    const natural = `${img.natural.width} x ${img.natural.height}`;
    const htmlWidth = img.attributes.width || '-';
    lines.push(
      `| ${i + 1} | ${img.filename} | ${rendered} | ${natural} | ${htmlWidth} |`
    );
  });

  return lines.join('\n');
}

function formatMarkdown(result) {
  const lines = [];
  lines.push('# Image Rendering Report');
  lines.push('');
  lines.push('## Measurement Info');
  lines.push('');
  lines.push('| Item | Value |');
  lines.push('|------|-------|');
  lines.push(`| URL | ${result.url} |`);
  lines.push(`| Timestamp | ${result.timestamp} |`);
  lines.push(
    `| Viewport | ${result.viewport.width} x ${result.viewport.height} |`
  );
  lines.push(`| Total Images | ${result.imageCount} |`);
  lines.push('');
  lines.push('## Image Details');
  lines.push('');
  lines.push(
    '| # | Filename | Rendered Width | Rendered Height | Natural Width | Natural Height | HTML Width |'
  );
  lines.push(
    '|---|----------|----------------|-----------------|---------------|----------------|------------|'
  );

  result.images.forEach((img, i) => {
    lines.push(
      `| ${i + 1} | ${img.filename} | ${img.rendered.width} | ${img.rendered.height} | ${img.natural.width} | ${img.natural.height} | ${img.attributes.width || '-'} |`
    );
  });

  lines.push('');
  lines.push('## Summary');
  lines.push('');

  if (result.images.length > 0) {
    const maxRenderedWidth = Math.max(...result.images.map((i) => i.rendered.width));
    const minRenderedWidth = Math.min(...result.images.map((i) => i.rendered.width));
    const avgRenderedWidth = Math.round(
      result.images.reduce((sum, i) => sum + i.rendered.width, 0) /
        result.images.length
    );

    lines.push(`- **Max Rendered Width**: ${maxRenderedWidth}px`);
    lines.push(`- **Min Rendered Width**: ${minRenderedWidth}px`);
    lines.push(`- **Avg Rendered Width**: ${avgRenderedWidth}px`);
  }

  return lines.join('\n');
}

function formatOutput(result, format) {
  switch (format) {
    case 'json':
      return JSON.stringify(result, null, 2);
    case 'markdown':
      return formatMarkdown(result);
    case 'table':
    default:
      return formatTable(result);
  }
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`
Image Rendering Measurement Tool

Usage:
  node measure.js <url> [options]

Options:
  --output, -o    Output file path (default: stdout)
  --format, -f    Output format: json, markdown, table (default: table)
  --viewport, -v  Viewport size WxH (default: 1920x1080)
  --headless      Run in headless mode (default: false)
  --min-size      Minimum image size to include (default: 50)

Examples:
  node measure.js https://example.com/page
  node measure.js https://example.com/page -f markdown -o report.md
  node measure.js https://example.com/page -f json -o result.json
`);
    process.exit(0);
  }

  const options = parseArgs(args);

  if (!options.url) {
    console.error('Error: URL is required');
    process.exit(1);
  }

  try {
    const result = await measureImages(options.url, options);
    const output = formatOutput(result, options.format);

    if (options.output) {
      fs.writeFileSync(options.output, output);
      console.error(`Report saved to: ${options.output}`);
    } else {
      console.log(output);
    }
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

main();
