import { getBaseUrl } from './get-base-url';

interface CanonicalUrlParams {
  lang: string;
  mdxPath: string[];
}

/**
 * Generate canonical URL for a page
 * @param params - Page parameters containing lang and mdxPath
 * @returns Canonical URL string
 */
export async function getCanonicalUrl(params: CanonicalUrlParams): Promise<string> {
  /**
   * NOTE(JK): We cannot use `getBaseUrl()` that relies on `headers()` here.
   * It will throw a DynamicServerError error while responding a request.
   * For more information on DynamicServerError, see:
   * https://nextjs.org/docs/messages/dynamic-server-error
   *
   * Instead, we use an environment variable VERCEL_ENV to determine the canonical URL.
   * VERCEL_ENV=production - https://docs.querypie.com
   * VERCEL_ENV=staging - https://docs-staging.querypie.io
   * VERCEL_ENV=preview - https://docs-preview.querypie.io
   * VERCEL_ENV=development - http://localhost:3000
   *
   * Please note that https://docs-preview.querypie.io does not exist and won't be set up.
   */
  const baseUrl = await getBaseUrl();
  const lang = params.lang || 'en';
  const pathSegments = params.mdxPath || [];
  const path = pathSegments.length > 0 ? `/${pathSegments.join('/')}` : '';
  return `${baseUrl}/${lang}${path}`;
}

