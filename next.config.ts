import nextra from 'nextra';

// Set up Nextra with its configuration
// Note: nextra includes remark-gfm by default, so no custom mdxOptions needed
const withNextra = nextra({
  latex: true,
  search: {
    codeblocks: false,
  },
  contentDirBasePath: '/',

  // To use standard HTML elements for your tables
  // but have them styled with components provided by useMDXComponents()
  // Refer to this: https://nextra.site/docs/advanced/table
  whiteListTagsStyling: ['table', 'thead', 'tbody', 'tr', 'th', 'td'],
});

// Export the final Next.js config with Nextra included
export default withNextra({
  poweredByHeader: process.env.NODE_ENV === 'development',
  reactStrictMode: process.env.NODE_ENV === 'development',
  i18n: {
    locales: ['en', 'ko', 'ja'],
    defaultLocale: 'en',
  },
  // Skip i18n for API routes
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return {
      beforeFiles: [
        // API 경로는 i18n 리다이렉트를 건너뛰도록 처리
        {
          source: '/api/:path*',
          destination: '/api/:path*',
          locale: false,
        },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
  // Configure redirects for Previous Version Documentation
  async redirects() {
    return [
      // querypie-overview -> overview 경로 변경에 대한 redirect (2026-01-22)
      {
        source: '/:locale(ko|en|ja)/querypie-overview/:path*',
        destination: '/:locale/overview/:path*',
        permanent: true,
      },
      {
        source: '/querypie-overview/:path*',
        destination: '/overview/:path*',
        permanent: true,
      },

      // Korean (ko) redirects
      {
        source: '/ko/querypie-manual/11.2.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/1291125198/',
        permanent: true,
      },
      {
        source: '/ko/querypie-manual/11.1.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/1171325037/',
        permanent: true,
      },
      {
        source: '/ko/querypie-manual/11.0.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/1071939590/',
        permanent: true,
      },
      {
        source: '/ko/querypie-manual/10.3.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/959545600/',
        permanent: true,
      },
      {
        source: '/ko/querypie-manual/10.2.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/736428087/',
        permanent: true,
      },
      {
        source: '/ko/querypie-manual/10.1.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/634519553/',
        permanent: true,
      },
      {
        source: '/ko/querypie-manual/10.0.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/579010917/',
        permanent: true,
      },
      {
        source: '/ko/querypie/9.20.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QS1/pages/524944097/',
        permanent: true,
      },

      // English (en) redirects
      {
        source: '/en/querypie-manual/11.0.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/1129677677/',
        permanent: true,
      },
      {
        source: '/en/querypie-manual/10.3.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/968950182/',
        permanent: true,
      },
      {
        source: '/en/querypie-manual/10.2.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/736756862/',
        permanent: true,
      },
      {
        source: '/en/querypie-manual/10.1.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/633799987/',
        permanent: true,
      },
      {
        source: '/en/querypie-manual/10.0.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/580224801/',
        permanent: true,
      },
      {
        source: '/en/querypie/9.16.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QS1/pages/369951121/',
        permanent: true,
      },

      // Japanese (ja) redirects
      {
        source: '/ja/querypie-manual/10.2.0/:path*',
        destination: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/834863167/',
        permanent: true,
      },
    ];
  },
});
