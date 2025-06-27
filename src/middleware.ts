import { middleware as nextraMiddleware } from 'nextra/locales';
import { NextRequest, NextResponse } from 'next/server';

// 로컬과 회사 GP IP입니다.
export const COMPANY_IPS = [
  '::1', // 로컬 ip6
  '127.0.0.1', // 로컬 ip4
  '13.209.86.91', // Global Protect
  '13.209.133.130', // Global Protect
  '114.141.122.75', // Global Protect
  '114.141.122.203', // Global Protect
  '165.85.47.212', // Global Protect
  '165.85.47.211', // Global Protect
  '165.225.228.0/23', // Zscaler
  '167.103.96.0/23', // Zscaler
];

/**
 * IP 주소가 CIDR 범위 내에 있는지 확인합니다.
 */
const isIPInCIDR = (ip: string, cidr: string): boolean => {
  // CIDR이 아닌 단일 IP인 경우
  if (!cidr.includes('/')) {
    return ip === cidr;
  }

  const [network, prefixLength] = cidr.split('/');
  const prefix = parseInt(prefixLength, 10);

  // IPv4 주소를 32비트 정수로 변환
  const ipToInt = (ipAddr: string): number => {
    return ipAddr.split('.').reduce((acc, octet) => (acc << 8) + parseInt(octet, 10), 0) >>> 0;
  };

  // 서브넷 마스크 생성
  const mask = (0xffffffff << (32 - prefix)) >>> 0;

  const ipInt = ipToInt(ip);
  const networkInt = ipToInt(network);

  return (ipInt & mask) === (networkInt & mask);
};

/**
 * 내부 요청인지 확인합니다.
 * COMPANY_IPS에 등록된 IP 주소 또는 IP 대역으로부터 요청이 온 경우 내부 요청으로 간주합니다.
 */
const isInternalRequest = (headers: Headers): boolean => {
  const clientIP = headers.get('x-real-ip') || headers.get('x-forwarded-for');

  if (!clientIP) {
    return false;
  }

  // x-forwarded-for 헤더에서 첫 번째 IP만 추출 (프록시 체인의 경우)
  const actualIP = clientIP.split(',')[0].trim();

  // COMPANY_IPS의 각 항목에 대해 검사
  return COMPANY_IPS.some(ipOrCidr => isIPInCIDR(actualIP, ipOrCidr));
};

export async function middleware(request: NextRequest) {
  if (process.env.DEPLOYMENT_ENV !== 'production' && !isInternalRequest(request.headers)) {
    return NextResponse.json({ error: 'Access denied' }, { status: 403 });
  }

  if (process.env.DEPLOYMENT_ENV === 'production' && request.nextUrl.pathname === '/robots.txt') {
    return new NextResponse(`User-agent: *
Allow: /
Sitemap: https://aihub-docs.app.querypie.com/sitemap.xml
      `);
  }

  if (process.env.DEPLOYMENT_ENV !== 'production' && request.nextUrl.pathname === '/robots.txt') {
    return new NextResponse(`User-agent: *
Disallow: /
      `);
  }

  return nextraMiddleware(request);
}

export const config = {
  // Matcher ignoring `/_next/` and `/api/`
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|icon.svg|apple-icon.png|manifest|_pagefind|sitemap.xml|icon-.*.png).*)',
  ],
};
