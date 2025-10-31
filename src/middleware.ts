import {middleware as nextraMiddleware} from 'nextra/locales';
import {NextRequest, NextResponse} from 'next/server';
import {middlewareLogger} from './lib/logger';
import {detectUserLanguage} from './lib/detect-user-language';

export async function middleware(request: NextRequest) {
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
