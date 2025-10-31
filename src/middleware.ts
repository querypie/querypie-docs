import {middleware as nextraMiddleware} from 'nextra/locales';
import {NextRequest, NextResponse} from 'next/server';
import {middlewareLogger} from './lib/logger';
import {detectUserLanguage} from './lib/detect-user-language';

// URIs that should skip Nextra middleware and be handled by route handlers
const SKIP_MIDDLEWARE_URIS = new Map<string, string>([
  // slugs[0]
  ['_next', 'Handled by Next.js'],
  ['robots.txt', 'Handled by static app route'],
  // slugs[0] - Served in public
  ['BingSiteAuth.xml', 'Served in public'],
  ['google7b73baf7a3209e6f.html', 'Served in public'],
  // slugs[0] - Handled in /src/app/
  ['favicon.ico', 'Handled by favicon.ico route handler'],
  // pathname
  ['/sitemap.xml', 'Served in public'],
  ['/en/sitemap.xml', 'Served in public'],
  ['/ja/sitemap.xml', 'Served in public'],
  ['/ko/sitemap.xml', 'Served in public'],
  // Add more URIs here as needed, for example,
]);

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const slugs = pathname.split('/').slice(1);

  // Skip Nextra middleware for URIs that should be handled by route handlers
  const skipBySlug = slugs.length > 0 && SKIP_MIDDLEWARE_URIS.has(slugs[0]);
  const skipByPathname = SKIP_MIDDLEWARE_URIS.has(pathname);
  if (skipBySlug || skipByPathname) {
    const reason = skipByPathname 
      ? SKIP_MIDDLEWARE_URIS.get(pathname)
      : (slugs.length > 0 ? SKIP_MIDDLEWARE_URIS.get(slugs[0]) : undefined);
    
    middlewareLogger.debug('Skipping Nextra middleware', {
      pathname,
      reason,
    });
    return NextResponse.next();
  }

  middlewareLogger.debug('Middleware request', {
    method: request.method,
    pathname,
  });

  // Handle root path redirect with dynamic language detection
  if (pathname === '/') {
    const detectedLanguage = detectUserLanguage(request);
    const redirectUrl = new URL(`/${detectedLanguage}/`, request.url);
    
    middlewareLogger.info('Root redirect with dynamic language detection', {
      from: '/',
      to: `/${detectedLanguage}/`,
      detectedLanguage,
      userAgent: request.headers.get('user-agent'),
      acceptLanguage: request.headers.get('accept-language'),
    });

    return NextResponse.redirect(redirectUrl);
  }

  middlewareLogger.debug('Handling with Nextra middleware');
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
