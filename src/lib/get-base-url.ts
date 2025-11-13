import { isStaticGeneration } from './is-static-generation';

/**
 * Get the base URL for the application.
 * During static generation (build time), returns the production URL.
 * During runtime, attempts to get the URL from request headers.
 * 
 * @returns Promise<string> The base URL
 */
export async function getBaseUrl(): Promise<string> {
  if (typeof window !== 'undefined') {
    throw new Error('getBaseUrl can only be used in server components');
  }

  // Production base URL used as fallback and for static generation
  const PRODUCTION_BASE_URL = 'https://docs.querypie.com';

  // Check if we're in static generation phase using isStaticGeneration()
  if (isStaticGeneration()) {
    return PRODUCTION_BASE_URL;
  }

  try {
    // Use dynamic import to conditionally load next/headers
    const { headers } = await import('next/headers');
    const headersList = await headers();
    const host = headersList.get('host');
    const protocol = headersList.get('x-forwarded-proto') || 'https';
    
    // If host is available, use it (runtime request)
    if (host) {
      return `${protocol}://${host}`;
    }
  } catch (error) {
    // headers() may throw an error in some edge cases
    // Log the error and fall back to production URL
    if (error instanceof Error) {
      console.warn('Error getting base URL from headers:', error.message);
    }
  }

  // Fallback to production URL when headers are unavailable
  return PRODUCTION_BASE_URL;
}
