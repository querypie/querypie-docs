import type { Metadata } from 'next';
import { extractDescriptionFromMdx } from '@/lib/extract-description';

/**
 * OG 이미지 메타데이터를 생성합니다.
 *
 * title과 description이 모두 유효한 경우에만 openGraph/twitter 메타데이터를 반환합니다.
 * description은 Nextra metadata에 없으면 MDX 본문에서 자동 추출합니다.
 */
export function buildOgMetadata(
  metadata: Metadata & { title?: string },
  mdxPath: string[],
  lang: string
): Pick<Metadata, 'openGraph' | 'twitter'> {
  const title = metadata.title ? String(metadata.title) : '';
  const description = metadata.description
    ? String(metadata.description)
    : extractDescriptionFromMdx(mdxPath, lang);

  if (!title || !description) {
    return {};
  }

  const ogPath = mdxPath.length > 0 ? `/${mdxPath.join('/')}` : '';
  const ogImageUrl = `/api/og/${lang}${ogPath}`;

  return {
    openGraph: {
      ...metadata.openGraph,
      images: [
        {
          url: ogImageUrl,
          width: 1200,
          height: 630,
          alt: title || 'QueryPie ACP Documentation',
        },
      ],
    },
    twitter: {
      ...metadata.twitter,
      card: 'summary_large_image' as const,
      images: [ogImageUrl],
    },
  };
}
