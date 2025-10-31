import {middleware as nextraMiddleware} from 'nextra/locales';
import {NextRequest, NextResponse} from 'next/server';
import {middlewareLogger} from './lib/logger';
import {detectUserLanguage} from './lib/detect-user-language';

// URIs that should skip Nextra middleware and be handled by route handlers
const SKIP_MIDDLEWARE_URIS = new Map<string, string>([
  ['/robots.txt', 'Handled by robots.txt route handler'],
  // Add more URIs here as needed, for example,
  // ['/manifest.json', 'Handled by manifest.json route handler'],
  // ['/sitemap.xml', 'Handled by sitemap.xml route handler'],
]);

export async function middleware(request: NextRequest) {
  // Skip Nextra middleware for URIs that should be handled by route handlers
  if (SKIP_MIDDLEWARE_URIS.has(request.nextUrl.pathname)) {
    middlewareLogger.debug('Skipping Nextra middleware', {
      pathname: request.nextUrl.pathname,
      reason: SKIP_MIDDLEWARE_URIS.get(request.nextUrl.pathname),
    });
    return NextResponse.next();
  }

  middlewareLogger.debug('Middleware request', {
    pathname: request.nextUrl.pathname,
    method: request.method
  });

  // Handle root path redirect with dynamic language detection
  if (request.nextUrl.pathname === '/') {
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
  // TODO(JK): Refer to this for more files to exclude, for example: manifest.json, ...
  // https://nextjs.org/docs/app/api-reference/file-conventions/metadata
  matcher: [
    '/((?!_next/static|_next/image|_pagefind|google*|.*\\.ico|.*\\.png|.*\\.mov|.*\\.xml).*)',
  ],
};
