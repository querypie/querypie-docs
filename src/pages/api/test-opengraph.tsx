import type { NextRequest } from 'next/server';
import { generateOgImage } from '@/lib/og-image';

export const config = {
  runtime: 'edge',
};

/**
 * 테스트용 OG 이미지 생성 endpoint.
 * query string으로 title, description을 전달받습니다.
 *
 * 예: /api/test-opengraph?title=Hello&description=World
 */
export default async function handler(req: NextRequest) {
  const { searchParams, origin } = new URL(req.url);
  const title = searchParams.get('title') || 'QueryPie ACP Product Documentation';
  const description = searchParams.get('description') || '';

  return generateOgImage(title, description, origin);
}
