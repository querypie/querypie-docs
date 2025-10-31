import {NextResponse} from 'next/server';
import isProduction from '@/lib/is-production';
import {getBaseUrl} from '@/lib/get-base-url';

export async function GET() {
  if (isProduction()) {
    const baseUrl = await getBaseUrl();
    return new NextResponse(`User-agent: *
Allow: /
Sitemap: ${baseUrl}/sitemap.xml
`);
  } else {
    return new NextResponse(`User-agent: *
Disallow: /
`);
  }
}
