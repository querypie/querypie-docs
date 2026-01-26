import { NextRequest } from 'next/server';
import { generateOgImage } from '@/lib/og-image';
import { extractTitleFromMdx, extractDescriptionFromMdx } from '@/lib/extract-description';

/**
 * Path 기반 OG 이미지 생성 endpoint.
 * MDX 파일을 내부에서 읽어 title/description을 추출합니다.
 *
 * 예: /api/og/en/administrator-manual/databases/monitoring
 */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ lang: string; mdxPath?: string[] }> }
) {
  const { lang, mdxPath = [] } = await params;
  const { origin } = new URL(req.url);

  const title = extractTitleFromMdx(mdxPath, lang) || 'QueryPie ACP Documentation';
  const description = extractDescriptionFromMdx(mdxPath, lang) || '';

  return generateOgImage(title, description, origin);
}
