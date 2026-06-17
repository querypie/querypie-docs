export type DocsSpotlightLocale = 'en' | 'ja' | 'ko';

export type DocsSpotlightItem = {
  id: string;
  date: string;
  href: string;
  imageSrc: string;
  imageAlt: string;
  title: string;
  spotlightMeta: string;
  visibleUntil: string;
};

export type ActiveDocsSpotlightItem = Omit<DocsSpotlightItem, 'visibleUntil'>;

export type DocsSpotlightContent = {
  ariaLabel: string;
  spotlightLabel: string;
  spotlightCtaLabel: string;
  spotlightDismissLabel: string;
  nextLabel: string;
  previousLabel: string;
  items: readonly DocsSpotlightItem[];
};

export type ActiveDocsSpotlightContent = Omit<DocsSpotlightContent, 'items'> & {
  items: readonly ActiveDocsSpotlightItem[];
};

type ActiveDocsSpotlightOptions = {
  random?: () => number;
  today?: string;
};

const datePattern = /^\d{4}-\d{2}-\d{2}$/;

export const docsSpotlightContent = {
  en: {
    ariaLabel: 'Latest company announcements',
    nextLabel: 'Next announcement',
    previousLabel: 'Previous announcement',
    spotlightCtaLabel: 'Read full story',
    spotlightDismissLabel: 'Dismiss spotlight',
    spotlightLabel: 'Spotlight',
    items: [
      {
        id: 'iso-42001-certification',
        date: '2026-06-04',
        href: '/news/24/iso-42001-certification-announcement',
        imageAlt: 'QueryPie Achieves ISO/IEC 42001 Certification for Its AI Management System',
        imageSrc: '/spotlight/iso-42001-certification/thumbnail.png',
        title: 'ISO/IEC 42001 Certification for AI Management System',
        spotlightMeta: 'June 4, 2026',
        visibleUntil: '2026-07-04',
      },
      {
        id: 'lingo-release',
        date: '2026-06-05',
        href: '/news/26/lingo-launch',
        imageAlt: 'QueryPie unveils Lingo, an AI real-time interpretation service',
        imageSrc: '/spotlight/lingo-release/hero-en.png',
        title: 'Lingo: AI Real-Time Interpretation Service',
        spotlightMeta: 'June 5, 2026',
        visibleUntil: '2026-07-05',
      },
      {
        id: 'notepie-release',
        date: '2026-06-09',
        href: '/news/27/notepie-launch',
        imageAlt: 'QueryPie Unveils NotePie, an AI Work Assistant Based on Documents and Web Sources',
        imageSrc: '/spotlight/notepie-release/hero-en.png',
        title: 'NotePie: AI Work Assistant for Documents and Web Sources',
        spotlightMeta: 'June 9, 2026',
        visibleUntil: '2026-07-09',
      },
      {
        id: 'ai-work-os-enterprise-intelligence',
        date: '2026-06-16',
        href: '/ko/blog/30/ai-work-os-enterprise-intelligence',
        imageAlt: 'AI Work OS: How a New Intelligence Works Inside the Enterprise',
        imageSrc: '/spotlight/ai-work-os-enterprise-intelligence/thumbnail.png',
        title: 'AI Work OS: How a New Intelligence Works Inside the Enterprise',
        spotlightMeta: 'June 16, 2026',
        visibleUntil: '2026-06-15',
      },
    ],
  },
  ja: {
    ariaLabel: '最新のお知らせ',
    nextLabel: '次のお知らせ',
    previousLabel: '前のお知らせ',
    spotlightCtaLabel: '詳しく見る',
    spotlightDismissLabel: 'Spotlightを閉じる',
    spotlightLabel: '注目',
    items: [
      {
        id: 'iso-42001-certification',
        date: '2026-06-04',
        href: '/news/24/iso-42001-certification-announcement',
        imageAlt: 'QueryPie AI、AIマネジメントシステムの国際規格 ISO/IEC 42001 認証を取得',
        imageSrc: '/spotlight/iso-42001-certification/thumbnail.png',
        title: 'AIマネジメントシステムの国際規格 ISO/IEC 42001 認証を取得',
        spotlightMeta: '2026年6月4日',
        visibleUntil: '2026-07-04',
      },
      {
        id: 'lingo-release',
        date: '2026-06-05',
        href: '/news/26/lingo-launch',
        imageAlt: 'QueryPie AI、AIリアルタイム通訳サービス「Lingo」を公開',
        imageSrc: '/spotlight/lingo-release/hero-ja.png',
        title: 'AIリアルタイム通訳サービス「Lingo」を公開',
        spotlightMeta: '2026年6月5日',
        visibleUntil: '2026-07-05',
      },
      {
        id: 'notepie-release',
        date: '2026-06-09',
        href: '/news/27/notepie-launch',
        imageAlt: 'QueryPie AI、文書・Web資料ベースのAI業務支援サービス「NotePie」を公開',
        imageSrc: '/spotlight/notepie-release/hero-ja.png',
        title: '文書・Web資料ベースのAI業務支援サービス「NotePie」を公開',
        spotlightMeta: '2026年6月9日',
        visibleUntil: '2026-07-09',
      },
      {
        id: 'ai-work-os-enterprise-intelligence',
        date: '2026-06-16',
        href: '/ko/blog/30/ai-work-os-enterprise-intelligence',
        imageAlt: 'AI Work OS：新しい知能が企業内で働く方法',
        imageSrc: '/spotlight/ai-work-os-enterprise-intelligence/thumbnail.png',
        title: 'AI Work OS：新しい知能が企業内で働く方法',
        spotlightMeta: '2026年6月16日',
        visibleUntil: '2026-06-15',
      },
    ],
  },
  ko: {
    ariaLabel: '회사 주요 소식',
    nextLabel: '다음 소식',
    previousLabel: '이전 소식',
    spotlightCtaLabel: '자세히 보기',
    spotlightDismissLabel: '하이라이트 닫기',
    spotlightLabel: '하이라이트',
    items: [
      {
        id: 'iso-42001-certification',
        date: '2026-06-04',
        href: '/news/24/iso-42001-certification-announcement',
        imageAlt: 'AI 경영시스템 국제 표준 ISO/IEC 42001 인증 획득',
        imageSrc: '/spotlight/iso-42001-certification/thumbnail.png',
        title: 'AI 경영시스템 국제 표준 ISO/IEC 42001 인증 획득',
        spotlightMeta: '2026년 6월 4일',
        visibleUntil: '2026-07-04',
      },
      {
        id: 'lingo-release',
        date: '2026-06-05',
        href: '/news/26/lingo-launch',
        imageAlt: 'AI 실시간 통역 서비스 ‘Lingo’ 공개',
        imageSrc: '/spotlight/lingo-release/hero-ko.png',
        title: 'AI 실시간 통역 서비스 ‘Lingo’ 공개',
        spotlightMeta: '2026년 6월 5일',
        visibleUntil: '2026-07-05',
      },
      {
        id: 'notepie-release',
        date: '2026-06-09',
        href: '/news/27/notepie-launch',
        imageAlt: '문서·웹 자료 기반 AI 업무 지원 서비스 ‘NotePie’ 공개',
        imageSrc: '/spotlight/notepie-release/hero-ko.png',
        title: '문서·웹 자료 기반 AI 업무 지원 서비스 ‘NotePie’ 공개',
        spotlightMeta: '2026년 6월 9일',
        visibleUntil: '2026-07-09',
      },
      {
        id: 'ai-work-os-enterprise-intelligence',
        date: '2026-06-16',
        href: '/ko/blog/30/ai-work-os-enterprise-intelligence',
        imageAlt: 'AI Work OS: 새로운 지능이 기업 안에서 일하는 방식',
        imageSrc: '/spotlight/ai-work-os-enterprise-intelligence/thumbnail.png',
        title: 'AI Work OS: 새로운 지능이 기업 안에서 일하는 방식',
        spotlightMeta: '2026년 6월 16일',
        visibleUntil: '2026-07-16',
      },
    ],
  },
} satisfies Record<DocsSpotlightLocale, DocsSpotlightContent>;

function todayInSeoul() {
  return new Intl.DateTimeFormat('en-CA', {
    day: '2-digit',
    month: '2-digit',
    timeZone: 'Asia/Seoul',
    year: 'numeric',
  }).format(new Date());
}

function shuffleItems(items: readonly DocsSpotlightItem[], random: () => number) {
  const shuffledItems = [...items];

  for (let index = shuffledItems.length - 1; index > 0; index -= 1) {
    const randomValue = Math.min(Math.max(random(), 0), 0.9999999999999999);
    const randomIndex = Math.floor(randomValue * (index + 1));
    const currentItem = shuffledItems[index];

    shuffledItems[index] = shuffledItems[randomIndex];
    shuffledItems[randomIndex] = currentItem;
  }

  return shuffledItems;
}

function orderActiveItems(items: readonly DocsSpotlightItem[], random: () => number) {
  if (items.length < 2) {
    return [...items];
  }

  const [latestItem, ...remainingItems] = [...items].sort((left, right) => right.date.localeCompare(left.date));

  return [latestItem, ...shuffleItems(remainingItems, random)];
}

function stripVisibleUntil(item: DocsSpotlightItem): ActiveDocsSpotlightItem {
  const { visibleUntil: _visibleUntil, ...activeItem } = item;

  return activeItem;
}

export function resolveDocsSpotlightLocale(locale: string | undefined): DocsSpotlightLocale {
  return locale === 'ja' || locale === 'ko' ? locale : 'en';
}

export function getActiveDocsSpotlightContent(
  locale: string | undefined,
  options: ActiveDocsSpotlightOptions = {},
): ActiveDocsSpotlightContent | null {
  const today = options.today ?? todayInSeoul();

  if (!datePattern.test(today)) {
    throw new Error('Expected docs spotlight today option to use YYYY-MM-DD format');
  }

  const content = docsSpotlightContent[resolveDocsSpotlightLocale(locale)];
  const activeItems = orderActiveItems(
    content.items.filter(item => item.visibleUntil >= today),
    options.random ?? Math.random,
  ).map(stripVisibleUntil);

  if (activeItems.length === 0) {
    return null;
  }

  return {
    ...content,
    items: activeItems,
  };
}
