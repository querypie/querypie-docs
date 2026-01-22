export default {
  index: {
    display: 'hidden',
  },
  // 2026-01-22 旧パスから新パスへのリダイレクト（SEOとブックマーク互換性）
  'querypie-overview': {
    type: 'redirect',
    href: '/ja/overview',
  },
  'overview': {
    type: 'page',
    title: '概要',
  },
  'user-manual': {
    type: 'page',
    title: 'ユーザーガイド',
  },
  'administrator-manual': {
    type: 'page',
    title: '管理者マニュアル',
  },
  'release-notes': {
    type: 'page',
    title: 'リリースノート',
  },
  'installation': {
    type: 'page',
    title: '製品インストールと技術サポート',
  },
  'api-reference': {
    type: 'page',
    title: 'APIリファレンス',
  },
  contactUs: {
    type: 'page',
    title: 'お問い合わせ',
    href: 'https://www.querypie.com/company/contact-us',
  },
};
