import { ImageResponse } from 'next/og';

const size = {
  width: 1200,
  height: 630,
};

// 원격 폰트 URL (TTF 형식 - ImageResponse에서 지원)
// Google Fonts에서 Noto Sans 사용 (영어/한국어/일본어 지원)
const FONT_URLS = {
  // Noto Sans - 라틴 문자용
  notoSans:
    'https://fonts.gstatic.com/s/notosans/v36/o-0mIpQlx3QUlC5A4PNB6Ryti20_6n1iPHjcz6L1SoM-jCpoiyD9A-9a6Vc.ttf',
  // Noto Sans JP - 일본어/한국어 CJK 문자용
  notoSansJP:
    'https://fonts.gstatic.com/s/notosansjp/v53/-F6jfjtqLzI2JPCgQBnw7HFyzSD-AsregP8VFBEi75vY0rw-oME.ttf',
};

async function loadFont(url: string): Promise<ArrayBuffer | null> {
  try {
    const response = await fetch(url);
    if (response.ok) {
      return await response.arrayBuffer();
    }
  } catch {
    // 폰트 로드 실패
  }
  return null;
}

// --- Module-level 캐싱 ---
// 폰트와 배경 이미지를 서버 인스턴스당 1회만 로드합니다.
// Serverless 환경에서 동일 인스턴스 내 후속 요청은 캐시된 데이터를 재사용합니다.

let cachedFonts: Promise<{ notoSans: ArrayBuffer | null; notoSansJP: ArrayBuffer | null }> | null =
  null;

function getFonts() {
  if (!cachedFonts) {
    cachedFonts = Promise.all([loadFont(FONT_URLS.notoSans), loadFont(FONT_URLS.notoSansJP)]).then(
      ([notoSans, notoSansJP]) => ({ notoSans, notoSansJP })
    );
  }
  return cachedFonts;
}

let cachedBackgroundImage: Promise<ArrayBuffer | null> | null = null;

function getBackgroundImage(origin: string) {
  if (!cachedBackgroundImage) {
    cachedBackgroundImage = fetch(`${origin}/og-background.png`)
      .then((res) => (res.ok ? res.arrayBuffer() : null))
      .catch(() => null);
  }
  return cachedBackgroundImage;
}

/**
 * OG 이미지를 생성합니다.
 *
 * @param title - 페이지 제목
 * @param description - 페이지 설명
 * @param origin - 배경 이미지를 로드하기 위한 origin URL (예: https://docs.querypie.com)
 */
export async function generateOgImage(
  title: string,
  description: string,
  origin: string
): Promise<ImageResponse> {
  // 리소스 병렬 로드 (캐시된 경우 즉시 반환)
  const [{ notoSans: notoSansFont, notoSansJP: notoSansJPFont }, backgroundImageData] =
    await Promise.all([getFonts(), getBackgroundImage(origin)]);

  // 배경 스타일
  const backgroundStyle = backgroundImageData
    ? {
        backgroundImage: `url(data:image/png;base64,${Buffer.from(backgroundImageData).toString('base64')})`,
        backgroundSize: 'cover' as const,
        backgroundPosition: 'center' as const,
      }
    : { backgroundColor: '#1a1a2e' };

  // 폰트 설정
  const fonts: { name: string; data: ArrayBuffer; style: 'normal' | 'italic' }[] = [];
  if (notoSansFont) {
    fonts.push({ name: 'Noto Sans', data: notoSansFont, style: 'normal' });
  }
  if (notoSansJPFont) {
    fonts.push({ name: 'Noto Sans JP', data: notoSansJPFont, style: 'normal' });
  }

  const fontFamily = fonts.length > 0 ? "'Noto Sans', 'Noto Sans JP', sans-serif" : undefined;

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-start',
          padding: '110px 72px 65px 72px',
          fontFamily,
          ...backgroundStyle,
        }}
      >
        {/* 제목 영역 - 최대 3줄 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            height: 240,
            marginBottom: 21,
          }}
        >
          <div
            style={
              {
                fontSize: 64,
                fontWeight: 700,
                color: '#ffffff',
                lineHeight: 1.2,
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '100%',
              } as React.CSSProperties
            }
          >
            {title}
          </div>
        </div>

        {/* 설명 영역 - 최대 4줄 */}
        {description && (
          <div
            style={
              {
                fontSize: 32,
                fontWeight: 400,
                color: 'rgba(255,255,255,0.85)',
                lineHeight: 1.5,
                display: '-webkit-box',
                WebkitLineClamp: 4,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '100%',
                maxHeight: 192,
              } as React.CSSProperties
            }
          >
            {description}
          </div>
        )}
      </div>
    ),
    {
      ...size,
      fonts: fonts.length > 0 ? fonts : undefined,
      headers: {
        'Cache-Control': 'public, max-age=86400, s-maxage=86400, stale-while-revalidate=604800',
      },
    }
  );
}
