import {NextResponse} from 'next/server';
import isProduction from '@/lib/is-production';
import {getBaseUrl} from '@/lib/get-base-url';

export async function GET() {
  if (isProduction()) {
    const baseUrl = await getBaseUrl();
    return new NextResponse(`User-agent: *
Allow: /

Disallow: /_next/
Disallow: /api/

Sitemap: ${baseUrl}/sitemap.xml
`);
  } else {
    return new NextResponse(`User-agent: *
Disallow: /
`);
  }
}
