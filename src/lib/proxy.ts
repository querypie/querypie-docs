import {NextRequest, NextResponse} from 'next/server';
import {proxyLogger} from './logger';
import {LRUCache} from './lru-cache';

// Configure target base URL
const TARGET_BASE_URL = 'https://docs.querypie.com';

// Configure your target path mappings here
const TARGET_PATH_MAPPINGS: Record<string, string> = {
  // QueryPie Documentation - All languages
  '/querypie/': '/querypie/',
  // QueryPie Manual Documentation - All languages
  '/querypie-manual/': '/querypie-manual/',
  // Theme and Asset files - All languages
  '/__theme/': '/__theme/',
  '/__assets-': '/__assets-',
  // Attachments - All languages
  '/__attachments/': '/__attachments/',
  // Chrome DevTools specific files - All languages
  '/.well-known/appspecific/com.chrome.devtools.json': '/.well-known/appspecific/com.chrome.devtools.json',
};

// Constants for header filtering
const EXCLUDED_REQUEST_HEADERS = ['host', 'x-forwarded-host', 'x-forwarded-proto'];
const EXCLUDED_RESPONSE_HEADERS = ['content-encoding', 'content-length', 'transfer-encoding'];



// Create cache instance for pathname matching results
const pathnameMatchCache = new LRUCache<string, { targetBaseUrl: string; remainingPath: string } | null>(10);

// Cache statistics
let cacheHits = 0;
let cacheMisses = 0;

/**
 * Log cache statistics periodically (every 100 requests)
 */
function logCacheStats() {
  const totalRequests = cacheHits + cacheMisses;
  if (totalRequests > 0) {
    const hitRate = ((cacheHits / totalRequests) * 100).toFixed(2);
    proxyLogger.info('Cache statistics', {
      cacheHits,
      cacheMisses,
      totalRequests,
      hitRate: `${hitRate}%`,
      cacheSize: pathnameMatchCache.size()
    });
  }
}

/**
 * Extract client IP from request headers
 */
function getClientIP(request: NextRequest): string {
  const ipHeaders = [
    'x-real-ip',
    'x-forwarded-for',
    'x-client-ip',
    'cf-connecting-ip',
    'x-forwarded',
    'forwarded-for',
    'forwarded'
  ];

  for (const header of ipHeaders) {
    const value = request.headers.get(header);
    if (value) {
      if (header === 'x-forwarded-for') {
        return value.split(',')[0]?.trim() || 'unknown';
      }
      return value;
    }
  }

  return process.env.NODE_ENV === 'development' ? '127.0.0.1' : 'unknown';
}

/**
 * Find matching prefix and return target URL information
 */
function findMatchingPrefix(pathname: string): { targetBaseUrl: string; remainingPath: string } | null {
  // Check cache first
  const cachedMatch = pathnameMatchCache.get(pathname);
  if (cachedMatch !== undefined) {
    cacheHits++;
    proxyLogger.debug('Cache hit for pathname', { pathname, cacheSize: pathnameMatchCache.size() });

    if ((cacheHits + cacheMisses) % 100 === 0) {
      logCacheStats();
    }
    return cachedMatch;
  }

  cacheMisses++;

  // Check direct prefix matches
  for (const [prefix, targetUrl] of Object.entries(TARGET_PATH_MAPPINGS)) {
    if (pathname.startsWith(prefix)) {
      const targetBaseUrl = `${TARGET_BASE_URL}${targetUrl}`;
      const remainingPath = pathname.substring(prefix.length);
      const result = { targetBaseUrl, remainingPath };
      pathnameMatchCache.set(pathname, result);
      return result;
    }
  }

  // Check for language-specific paths (2-letter language codes)
  const langMatch = pathname.match(/^\/([a-z]{2})\//);
  if (langMatch) {
    const langCode = langMatch[1];
    for (const [prefix, targetUrl] of Object.entries(TARGET_PATH_MAPPINGS)) {
      const langPrefix = `/${langCode}${prefix}`;
      if (pathname.startsWith(langPrefix)) {
        const targetBaseUrl = `${TARGET_BASE_URL}/${langCode}${targetUrl}`;
        const remainingPath = pathname.substring(langPrefix.length);
        const result = { targetBaseUrl, remainingPath };
        pathnameMatchCache.set(pathname, result);
        return result;
      }
    }
  }

  pathnameMatchCache.set(pathname, null);
  return null;
}

/**
 * Rewrite URLs in HTML content to use proxy URLs
 */
function rewriteUrlsInHtml(htmlContent: string, proxyOrigin: string): string {
  const rewrittenHtml = htmlContent.replace(/https:\/\/docs\.querypie\.com/g, proxyOrigin);
  
  const originalCount = (htmlContent.match(/https:\/\/docs\.querypie\.com/g) || []).length;
  proxyLogger.debug('URL rewrite completed', { originalCount, rewrittenCount: originalCount });
  
  return rewrittenHtml;
}

/**
 * Check if two URLs are similar except for trailing slash
 */
function areUrlsSimilarExceptTrailingSlash(url1: string, url2: string): boolean {
  const getPathname = (url: string) => {
    try {
      return new URL(url).pathname;
    } catch {
      return url.startsWith('/') ? url : `/${url}`;
    }
  };
  
  const normalize = (path: string) => path.endsWith('/') ? path.slice(0, -1) : path;
  const normalized1 = normalize(getPathname(url1));
  const normalized2 = normalize(getPathname(url2));
  
  proxyLogger.debug('URL similarity check', {
    url1, url2, normalized1, normalized2, isSimilar: normalized1 === normalized2
  });
  
  return normalized1 === normalized2;
}

/**
 * Convert location URL to target or proxy URL
 */
function convertLocationUrl(
  location: string, 
  baseUrl: string, 
  currentPath?: string
): string {
  if (location.startsWith('http')) {
    return location.startsWith(TARGET_BASE_URL) 
      ? `${baseUrl}${location.substring(TARGET_BASE_URL.length)}`
      : location;
  }
  
  if (location.startsWith('/')) {
    return `${baseUrl}${location}`;
  }
  
  // Relative URL
  const currentDir = currentPath 
    ? currentPath.substring(0, currentPath.lastIndexOf('/') + 1)
    : '/';
  return `${baseUrl}${currentDir}${location}`;
}

/**
 * Prepare headers for proxy request
 */
function prepareProxyHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  
  request.headers.forEach((value, key) => {
    if (!EXCLUDED_REQUEST_HEADERS.includes(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const clientIP = getClientIP(request);
  headers.set('x-forwarded-for', clientIP);
  headers.set('x-forwarded-proto', request.nextUrl.protocol);
  headers.set('x-forwarded-host', request.nextUrl.host);

  return headers;
}

/**
 * Create response headers from original response
 */
function createResponseHeaders(response: Response): Headers {
  const responseHeaders = new Headers();
  response.headers.forEach((value, key) => {
    if (!EXCLUDED_RESPONSE_HEADERS.includes(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });
  return responseHeaders;
}

/**
 * Make a fetch request with common configuration
 */
async function makeFetchRequest(
  url: string,
  request: NextRequest,
  headers?: Headers,
  additionalHeaders?: Record<string, string>
): Promise<Response> {
  const requestHeaders = headers || prepareProxyHeaders(request);
  
  if (additionalHeaders) {
    Object.entries(additionalHeaders).forEach(([key, value]) => {
      requestHeaders.set(key, value);
    });
  }

  return fetch(url, {
    method: request.method,
    headers: requestHeaders,
    body: request.body,
    redirect: 'manual',
  });
}

/**
 * Handle 304 Not Modified response by fetching actual content
 */
async function handle304Response(request: NextRequest, targetUrl: string): Promise<Response> {
  proxyLogger.debug('304 Not Modified detected, fetching actual content');

  const noCacheHeaders = {
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'if-none-match': '',
    'if-modified-since': ''
  };

  const response = await makeFetchRequest(targetUrl, request, undefined, noCacheHeaders);
  
  proxyLogger.info('304 bypass response', {
    status: response.status,
    statusText: response.statusText
  });

  return response;
}

/**
 * Handle trailing slash redirects by making a direct request
 */
async function handleTrailingSlashRedirect(
  request: NextRequest,
  response: Response,
  location: string,
  targetBaseUrl: string,
  remainingPath: string
): Promise<Response | null> {
  if (!areUrlsSimilarExceptTrailingSlash(request.nextUrl.href, location)) {
    return null;
  }

  proxyLogger.info('Trailing slash redirect detected, making direct request', {
    currentUrl: request.nextUrl.href,
    location,
    status: response.status
  });

  const targetUrl = convertLocationUrl(location, TARGET_BASE_URL, remainingPath ? `${targetBaseUrl}${remainingPath}` : targetBaseUrl);

  try {
    const directResponse = await makeFetchRequest(targetUrl, request);
    
    proxyLogger.info('Direct request completed for trailing slash redirect', {
      status: directResponse.status,
      statusText: directResponse.statusText,
      contentType: directResponse.headers.get('content-type') || 'unknown'
    });

    return directResponse;
  } catch (error) {
    proxyLogger.error('Direct request failed for trailing slash redirect', {
      error: error instanceof Error ? error.message : String(error),
      targetUrl
    });
    return null;
  }
}

/**
 * Process response based on content type
 */
async function processResponse(response: Response, request: NextRequest): Promise<NextResponse> {
  const responseHeaders = createResponseHeaders(response);
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('text/html') && response.body) {
    const htmlContent = await response.text();
    const rewrittenHtml = rewriteUrlsInHtml(htmlContent, request.nextUrl.origin);
    
    return new NextResponse(rewrittenHtml, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  }

  return new NextResponse(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

/**
 * Handle redirect response by modifying location header
 */
function handleRedirectResponse(response: Response, request: NextRequest, location: string): NextResponse {
  proxyLogger.info('Redirect detected', {
    status: response.status,
    location,
    originalRequestUrl: request.nextUrl.href
  });

  const responseHeaders = createResponseHeaders(response);
  const proxyLocation = convertLocationUrl(location, request.nextUrl.origin, request.nextUrl.pathname);
  
  responseHeaders.set('location', proxyLocation);

  return new NextResponse(null, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

/**
 * Handle proxy request by forwarding to target URL
 */
export async function handleProxyRequest(request: NextRequest): Promise<NextResponse> {
  const pathname = request.nextUrl.pathname;
  const clientIP = getClientIP(request);

  try {
    proxyLogger.info('Proxy request received', {
      method: request.method,
      pathname,
      search: request.nextUrl.search,
      clientIP
    });

    const match = findMatchingPrefix(pathname);
    if (!match) {
      proxyLogger.info('No matching prefix found', { pathname });
      return new NextResponse('Service not found', { status: 404 });
    }

    const { targetBaseUrl, remainingPath } = match;
    const targetUrl = remainingPath ? `${targetBaseUrl}${remainingPath}` : targetBaseUrl;
    const finalUrl = `${targetUrl}${request.nextUrl.search}`;

    proxyLogger.debug('Forwarding request', { finalUrl });

    let response = await makeFetchRequest(finalUrl, request);

    proxyLogger.info('Proxy response received', {
      status: response.status,
      statusText: response.statusText,
      contentType: response.headers.get('content-type') || 'unknown'
    });

    // Handle 304 Not Modified
    if (response.status === 304) {
      response = await handle304Response(request, finalUrl);
    }

    // Handle redirects
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get('location');
      if (location) {
        const directResponse = await handleTrailingSlashRedirect(
          request, response, location, targetBaseUrl, remainingPath
        );

        if (directResponse) {
          proxyLogger.info('Using direct response instead of redirect', {
            status: directResponse.status,
            statusText: directResponse.statusText
          });
          return await processResponse(directResponse, request);
        }

        return handleRedirectResponse(response, request, location);
      }
      
      proxyLogger.warn('Redirect status but no location header', { status: response.status });
    }

    return await processResponse(response, request);

  } catch (error) {
    proxyLogger.error('Proxy request failed', {
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined
    });
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}

/**
 * Check if the request path should be proxied
 */
export function shouldProxy(pathname: string): boolean {
  proxyLogger.debug('shouldProxy check', { pathname });
  const match = findMatchingPrefix(pathname);
  const shouldProxy = !!match;
  proxyLogger.debug(shouldProxy ? 'Match found' : 'No match found', { pathname });
  return shouldProxy;
}