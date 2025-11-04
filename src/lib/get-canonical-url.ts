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
  const baseUrl = await getBaseUrl();
  const lang = params.lang || 'en';
  const pathSegments = params.mdxPath || [];
  const path = pathSegments.length > 0 ? `/${pathSegments.join('/')}` : '';
  return `${baseUrl}/${lang}${path}`;
}

