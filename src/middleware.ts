import {middleware as nextraMiddleware} from 'nextra/locales';
import {NextRequest, NextResponse} from 'next/server';
import {handleProxyRequest, shouldProxy} from './lib/proxy';
import {middlewareLogger} from './lib/logger';

// Supported languages
const supportedLanguages = ['en', 'ko', 'ja'];
const defaultLanguage = 'en';

// Language detection function
function detectUserLanguage(request: NextRequest): string {
  // Check Accept-Language header
  const acceptLanguage = request.headers.get('accept-language');
  if (acceptLanguage) {
    // Parse Accept-Language header (e.g., "ko-KR,ko;q=0.9,en;q=0.8")
    const languages = acceptLanguage
      .split(',')
      .map(lang => {
        const [code, qValue] = lang.trim().split(';q=');
        return {
          code: code.split('-')[0], // Extract language code (ko from ko-KR)
          quality: qValue ? parseFloat(qValue) : 1.0
        };
      })
      .sort((a, b) => b.quality - a.quality);

    // Find the first supported language
    for (const lang of languages) {
      if (supportedLanguages.includes(lang.code)) {
        middlewareLogger.debug('Language detected from Accept-Language header', { 
          lang: lang.code, 
          quality: lang.quality,
          acceptLanguage 
        });
        return lang.code;
      }
    }
  }

  // Default fallback
  middlewareLogger.debug('Using default language', { lang: defaultLanguage });
  return defaultLanguage;
}

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

  if (request.nextUrl.pathname === '/robots.txt') {
    middlewareLogger.debug('Handling robots.txt request');
    if (process.env.DEPLOYMENT_ENV === 'production') {
      return new NextResponse(`User-agent: *
Allow: /
Sitemap: https://docs.querypie.com/sitemap.xml
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
