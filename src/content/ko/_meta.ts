export default {
  index: {
    display: 'hidden',
  },
  // 2026-01-22 기존 경로에서 새 경로로 redirect (SEO 및 북마크 호환성)
  'querypie-overview': {
    type: 'redirect',
    href: '/ko/overview',
  },
  'overview': {
    type: 'page',
    title: 'QueryPie Overview',
  },
  'user-manual': {
    type: 'page',
    title: '사용자 매뉴얼',
  },
  'administrator-manual': {
    type: 'page',
    title: '관리자 매뉴얼',
  },
  'release-notes': {
    type: 'page',
    title: '릴리즈 노트',
  },
  'installation': {
    type: 'page',
    title: '제품 설치와 기술지원',
  },
  'api-reference': {
    type: 'page',
    title: 'API 레퍼런스',
  },
  contactUs: {
    type: 'page',
    title: '문의하기',
    href: 'https://www.querypie.com/company/contact-us',
  },
};
