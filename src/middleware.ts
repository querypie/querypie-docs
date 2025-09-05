import {middleware as nextraMiddleware} from 'nextra/locales';
import {NextRequest, NextResponse} from 'next/server';
import {handleProxyRequest, shouldProxy} from './lib/proxy';
import {middlewareLogger} from './lib/logger';

export async function middleware(request: NextRequest) {
  middlewareLogger.debug('Middleware request', {
    pathname: request.nextUrl.pathname,
    method: request.method
  });

  if (request.nextUrl.pathname === '/robots.txt') {
    middlewareLogger.debug('Handling robots.txt request');
    if (process.env.DEPLOYMENT_ENV === 'production') {
      return new NextResponse(`User-agent: *
Allow: /
Sitemap: https://docs.querypie.com/sitemap.xml
Sitemap: https://docs.querypie.io/sitemap.xml
Sitemap: https://querypie-docs.vercel.app/sitemap.xml
`);
    } else {
      return new NextResponse(`User-agent: *
Disallow: /
`);
    }
  }

  // Handle proxy requests before Nextra routing
  if (shouldProxy(request.nextUrl.pathname)) {
    middlewareLogger.debug('Proxy request detected, handling with proxy');
    return handleProxyRequest(request);
  }

  middlewareLogger.debug('Handling with Nextra middleware');
  return nextraMiddleware(request);
}

export const config = {
  // Matcher ignoring `/_next/` and `/api/`
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|icon.svg|apple-icon.png|manifest|_pagefind|sitemap.xml|icon-.*.png).*)',
  ],
};
