import nextra from 'nextra';
import remarkEmoji from 'remark-emoji';
import remarkGfm from 'remark-gfm';
import rehypeAttrs from 'rehype-attr';

// Set up Nextra with its configuration
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

  // Add remark plugins for emoji and GitHub Flavored Markdown support
  mdxOptions: {
    remarkPlugins: [remarkEmoji, remarkGfm],
    rehypePlugins: [
      [rehypeAttrs, { properties: ['width', 'class'] }]
    ],
  },
});

// Export the final Next.js config with Nextra included
export default withNextra({
  eslint: {
    ignoreDuringBuilds: true,
  },
  poweredByHeader: process.env.NODE_ENV === 'development',
  reactStrictMode: process.env.NODE_ENV === 'development',
  i18n: {
    locales: ['en', 'ko', 'ja'],
    defaultLocale: 'en',
  },
  serverRuntimeConfig: {
    // Enable IP address extraction
    trustProxy: true,
  },
  // Configure redirects for Previous Version Documentation
  async redirects() {
    return [
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
  // Configure webpack to use memory cache to avoid large string serialization warnings
  webpack: (config, { dev, isServer }) => {
    // Use memory cache for better performance and to avoid serialization warnings
    config.cache = {
      type: 'memory',
    };
    return config;
  },
});
