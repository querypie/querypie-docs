import { middleware as nextraMiddleware } from 'nextra/locales';
import { NextRequest, NextResponse } from 'next/server';
import { proxyLogger } from './lib/logger';
import { detectUserLanguage, supportedLanguages } from './lib/detect-user-language';

// URIs that should skip Nextra middleware and be handled by route handlers
const SKIP_MIDDLEWARE_URIS = new Map<string, string>([
  // slugs[0]
  ['_next', 'Handled by Next.js'],
  ['robots.txt', 'Handled by route handler'],
  ['.well-known', 'Handled by route handler'],
  ['api', 'Handled by API route handler'],
  // slugs[0] - Served in public
  ['BingSiteAuth.xml', 'Served in public'],
  ['google7b73baf7a3209e6f.html', 'Served in public'],
  ['openapi-specification', 'Served in public'],
  // slugs[0] - Handled in /src/app/
  ['favicon.ico', 'Handled by favicon.ico route handler'],
  // pathname
  ['/sitemap.xml', 'Served in public'],
  ['/en/sitemap.xml', 'Served in public'],
  ['/ja/sitemap.xml', 'Served in public'],
  ['/ko/sitemap.xml', 'Served in public'],
  // Add more URIs here as needed, for example,
]);

/**
 * Splits pathname into slugs and ensures at least one element exists.
 * For root path '/', returns [''] to ensure slugs[0] is always accessible.
 * @param pathname The pathname to split
 * @returns Array of slugs with at least one element
 */
function getSlugs(pathname: string): string[] {
  const slugs = pathname.split('/').slice(1);
  // Ensure at least one element exists (empty string for root path)
  return slugs.length > 0 ? slugs : [''];
}

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const slugs = getSlugs(pathname);

  // Skip Nextra middleware for URIs that should be handled by route handlers
  const skipBySlug = SKIP_MIDDLEWARE_URIS.has(slugs[0]);
  const skipByPathname = SKIP_MIDDLEWARE_URIS.has(pathname);
  if (skipBySlug || skipByPathname) {
    const reason = skipBySlug ? SKIP_MIDDLEWARE_URIS.get(slugs[0]) : SKIP_MIDDLEWARE_URIS.get(pathname);

    proxyLogger.debug('Skipping Nextra Proxy', {
      pathname,
      reason,
    });
    return NextResponse.next();
  }

  proxyLogger.debug('Proxy request', {
    method: request.method,
    pathname,
  });

  // Handle path rewrite when the first segment is not a supported language
  const needsLanguagePrefix = !supportedLanguages.includes(slugs[0]);
  if (needsLanguagePrefix && pathname === '/') {
    // NOTE(JK): Apply only for the root path, not subpaths.
    // Or, pages on the left sidebar won't be listed.
    const detectedLanguage = detectUserLanguage(request);
    const rewriteUrl = new URL(`/${detectedLanguage}${pathname}`, request.url);

    if (detectedLanguage === 'en') {
      proxyLogger.info('Root rewrite with dynamic language detection', {
        from: pathname,
        to: rewriteUrl,
        acceptLanguage: request.headers.get('accept-language'),
      });
      return NextResponse.rewrite(rewriteUrl);
    } else {
      proxyLogger.info('Root redirect with dynamic language detection', {
        from: pathname,
        to: rewriteUrl,
        acceptLanguage: request.headers.get('accept-language'),
      });
      return NextResponse.redirect(rewriteUrl);
    }
  }

  proxyLogger.debug('Handling with Nextra middleware');
  return nextraMiddleware(request);
}

export const config = {
  // Matcher for specific routes that need middleware processing
  // NOTE(JK): Refer to this for more files to exclude, for example, manifest.json, ...
  // https://nextjs.org/docs/app/api-reference/file-conventions/metadata
  matcher: [
    // NOTE(JK): Add attachment file patterns here that need to be processed
    // under directories such as public/user-manual/.
    '/((?!_next/static|_next/image|_pagefind/|.*\\.png|.*\\.mov).*)',
  ],
};
