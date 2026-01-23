#!/usr/bin/env node

/**
 * Image Rendering Comparison Tool
 *
 * Compares rendered image sizes between two web pages using Playwright.
 *
 * Usage:
 *   node compare.js <url1> <url2> [options]
 *
 * Options:
 *   --output, -o    Output file path (default: stdout)
 *   --format, -f    Output format: json, markdown, table (default: table)
 *   --viewport, -v  Viewport size WxH (default: 1920x1080)
 *   --headless      Run in headless mode (default: false)
 *   --label1        Label for first URL (default: URL1)
 *   --label2        Label for second URL (default: URL2)
 *
 * Examples:
 *   node compare.js https://site1.com/page https://site2.com/page
 *   node compare.js https://vercel-preview.com/page https://confluence.com/page --label1 "Vercel" --label2 "Confluence"
 */

import { chromium } from 'playwright';
import fs from 'fs';

function parseArgs(args) {
  const options = {
    urls: [],
    output: null,
    format: 'table',
    viewport: { width: 1920, height: 1080 },
    headless: false,
    minSize: 50,
    label1: 'URL1',
    label2: 'URL2',
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg.startsWith('http://') || arg.startsWith('https://')) {
      options.urls.push(arg);
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
    } else if (arg === '--label1') {
      options.label1 = args[++i];
    } else if (arg === '--label2') {
      options.label2 = args[++i];
    }
  }

  return options;
}

async function measureImages(page, url, minSize) {
  console.error(`Loading: ${url}`);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(3000);

  const images = await page.evaluate((minSize) => {
    const imgs = document.querySelectorAll('img');
    return Array.from(imgs)
      .map((img, index) => {
        const rect = img.getBoundingClientRect();
        const src = img.src || img.getAttribute('src') || '';

        let filename = '';
        try {
          const urlObj = new URL(src, window.location.origin);
          const pathname = urlObj.pathname;
          filename = decodeURIComponent(pathname.split('/').pop() || src);
        } catch {
          filename = src.split('/').pop() || src;
        }

        return {
          index,
          filename,
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
          },
        };
      })
      .filter(
        (img) =>
          img.rendered.width >= minSize && img.rendered.height >= minSize
      );
  }, minSize);

  return images;
}

function matchImages(images1, images2) {
  const comparisons = [];

  // Try to match by filename first
  const used2 = new Set();

  for (const img1 of images1) {
    let matched = null;

    // Exact filename match
    for (const img2 of images2) {
      if (!used2.has(img2.index) && img1.filename === img2.filename) {
        matched = img2;
        used2.add(img2.index);
        break;
      }
    }

    // If no exact match, try by index position
    if (!matched) {
      for (const img2 of images2) {
        if (!used2.has(img2.index) && img1.index === img2.index) {
          matched = img2;
          used2.add(img2.index);
          break;
        }
      }
    }

    comparisons.push({
      filename: img1.filename,
      url1: img1,
      url2: matched,
    });
  }

  // Add unmatched images from URL2
  for (const img2 of images2) {
    if (!used2.has(img2.index)) {
      comparisons.push({
        filename: img2.filename,
        url1: null,
        url2: img2,
      });
    }
  }

  return comparisons;
}

function formatTable(result, options) {
  const lines = [];
  lines.push('Image Rendering Comparison Report');
  lines.push('='.repeat(50));
  lines.push(`${options.label1}: ${result.url1}`);
  lines.push(`${options.label2}: ${result.url2}`);
  lines.push(`Timestamp: ${result.timestamp}`);
  lines.push(`Viewport: ${result.viewport.width}x${result.viewport.height}`);
  lines.push('');
  lines.push(
    `| # | Filename | ${options.label1} (WxH) | ${options.label2} (WxH) | Width Diff |`
  );
  lines.push('|---|----------|----------------|----------------|------------|');

  result.comparisons.forEach((comp, i) => {
    const filename =
      comp.filename.length > 30
        ? comp.filename.substring(0, 27) + '...'
        : comp.filename;

    const size1 = comp.url1
      ? `${comp.url1.rendered.width} x ${comp.url1.rendered.height}`
      : '-';
    const size2 = comp.url2
      ? `${comp.url2.rendered.width} x ${comp.url2.rendered.height}`
      : '-';

    let diff = '-';
    if (comp.url1 && comp.url2) {
      const widthDiff = comp.url1.rendered.width - comp.url2.rendered.width;
      if (widthDiff === 0) {
        diff = '0';
      } else if (widthDiff > 0) {
        diff = `+${widthDiff}`;
      } else {
        diff = `${widthDiff}`;
      }
    }

    lines.push(`| ${i + 1} | ${filename} | ${size1} | ${size2} | ${diff} |`);
  });

  lines.push('');
  lines.push('Summary:');
  lines.push(`  Matched: ${result.summary.matched}`);
  lines.push(`  Exact match: ${result.summary.exactMatch}`);
  lines.push(`  Only in ${options.label1}: ${result.summary.onlyUrl1}`);
  lines.push(`  Only in ${options.label2}: ${result.summary.onlyUrl2}`);

  return lines.join('\n');
}

function formatMarkdown(result, options) {
  const lines = [];
  lines.push('# Image Rendering Comparison Report');
  lines.push('');
  lines.push('## Measurement Info');
  lines.push('');
  lines.push('| Item | Value |');
  lines.push('|------|-------|');
  lines.push(`| **${options.label1}** | ${result.url1} |`);
  lines.push(`| **${options.label2}** | ${result.url2} |`);
  lines.push(`| **Timestamp** | ${result.timestamp} |`);
  lines.push(
    `| **Viewport** | ${result.viewport.width} x ${result.viewport.height} |`
  );
  lines.push('');
  lines.push('## Comparison Results');
  lines.push('');
  lines.push(
    `| # | Filename | ${options.label1} Width | ${options.label1} Height | ${options.label2} Width | ${options.label2} Height | Diff | Status |`
  );
  lines.push(
    '|---|----------|------------|-------------|------------|-------------|------|--------|'
  );

  result.comparisons.forEach((comp, i) => {
    const filename =
      comp.filename.length > 35
        ? comp.filename.substring(0, 32) + '...'
        : comp.filename;

    const w1 = comp.url1 ? comp.url1.rendered.width : '-';
    const h1 = comp.url1 ? comp.url1.rendered.height : '-';
    const w2 = comp.url2 ? comp.url2.rendered.width : '-';
    const h2 = comp.url2 ? comp.url2.rendered.height : '-';

    let diff = '-';
    let status = '';

    if (!comp.url1) {
      status = `Only in ${options.label2}`;
    } else if (!comp.url2) {
      status = `Only in ${options.label1}`;
    } else {
      const widthDiff = comp.url1.rendered.width - comp.url2.rendered.width;
      if (widthDiff === 0) {
        diff = '0';
        status = 'Exact';
      } else if (Math.abs(widthDiff) <= 2) {
        diff = widthDiff > 0 ? `+${widthDiff}` : `${widthDiff}`;
        status = 'Near';
      } else {
        diff = widthDiff > 0 ? `+${widthDiff}` : `${widthDiff}`;
        status = 'Diff';
      }
    }

    lines.push(
      `| ${i + 1} | ${filename} | ${w1} | ${h1} | ${w2} | ${h2} | ${diff} | ${status} |`
    );
  });

  lines.push('');
  lines.push('## Summary');
  lines.push('');
  lines.push(`| Metric | Count |`);
  lines.push(`|--------|-------|`);
  lines.push(`| Total Comparisons | ${result.comparisons.length} |`);
  lines.push(`| Matched Images | ${result.summary.matched} |`);
  lines.push(`| Exact Width Match | ${result.summary.exactMatch} |`);
  lines.push(`| Near Match (<=2px) | ${result.summary.nearMatch} |`);
  lines.push(`| Only in ${options.label1} | ${result.summary.onlyUrl1} |`);
  lines.push(`| Only in ${options.label2} | ${result.summary.onlyUrl2} |`);

  return lines.join('\n');
}

function formatOutput(result, format, options) {
  switch (format) {
    case 'json':
      return JSON.stringify(result, null, 2);
    case 'markdown':
      return formatMarkdown(result, options);
    case 'table':
    default:
      return formatTable(result, options);
  }
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`
Image Rendering Comparison Tool

Usage:
  node compare.js <url1> <url2> [options]

Options:
  --output, -o    Output file path (default: stdout)
  --format, -f    Output format: json, markdown, table (default: table)
  --viewport, -v  Viewport size WxH (default: 1920x1080)
  --headless      Run in headless mode (default: false)
  --label1        Label for first URL (default: URL1)
  --label2        Label for second URL (default: URL2)

Examples:
  node compare.js https://site1.com/page https://site2.com/page
  node compare.js https://vercel.app/page https://confluence.com/page \\
    --label1 "Vercel" --label2 "Confluence" -f markdown -o report.md
`);
    process.exit(0);
  }

  const options = parseArgs(args);

  if (options.urls.length < 2) {
    console.error('Error: Two URLs are required');
    process.exit(1);
  }

  const browser = await chromium.launch({
    headless: options.headless,
    args: ['--window-size=1920,1080'],
  });

  const context = await browser.newContext({
    viewport: options.viewport,
  });

  const page = await context.newPage();

  try {
    const images1 = await measureImages(page, options.urls[0], options.minSize);
    const images2 = await measureImages(page, options.urls[1], options.minSize);

    const comparisons = matchImages(images1, images2);

    // Calculate summary
    let matched = 0;
    let exactMatch = 0;
    let nearMatch = 0;
    let onlyUrl1 = 0;
    let onlyUrl2 = 0;

    for (const comp of comparisons) {
      if (comp.url1 && comp.url2) {
        matched++;
        const widthDiff = Math.abs(
          comp.url1.rendered.width - comp.url2.rendered.width
        );
        if (widthDiff === 0) exactMatch++;
        else if (widthDiff <= 2) nearMatch++;
      } else if (comp.url1) {
        onlyUrl1++;
      } else {
        onlyUrl2++;
      }
    }

    const result = {
      url1: options.urls[0],
      url2: options.urls[1],
      timestamp: new Date().toISOString(),
      viewport: options.viewport,
      comparisons,
      summary: {
        total: comparisons.length,
        matched,
        exactMatch,
        nearMatch,
        onlyUrl1,
        onlyUrl2,
      },
    };

    const output = formatOutput(result, options.format, options);

    if (options.output) {
      fs.writeFileSync(options.output, output);
      console.error(`Report saved to: ${options.output}`);
    } else {
      console.log(output);
    }
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
