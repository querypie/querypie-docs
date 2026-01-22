export default {
  index: {
    display: 'hidden',
  },
  // 2026-01-22 Redirect from old path to new path (SEO and bookmark compatibility)
  'querypie-overview': {
    type: 'redirect',
    href: '/en/overview',
  },
  'overview': {
    type: 'page',
    title: 'Overview',
  },
  'user-manual': {
    type: 'page',
    title: 'User Manual',
  },
  'administrator-manual': {
    type: 'page',
    title: 'Administrator Manual',
  },
  'release-notes': {
    type: 'page',
    title: 'Release Notes',
  },
  'installation': {
    type: 'page',
    title: 'Installation and Technical Support',
  },
  'api-reference': {
    type: 'page',
    title: 'API Reference',
  },
  contactUs: {
    type: 'page',
    title: 'Contact Us',
    href: 'https://www.querypie.com/company/contact-us',
  },
};
