import nextra from 'nextra';

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
  // Configure webpack to use memory cache to avoid large string serialization warnings
  webpack: (config, { dev, isServer }) => {
    // Use memory cache for better performance and to avoid serialization warnings
    config.cache = {
      type: 'memory',
    };
    return config;
  },
  async redirects() {
    return [
      {
        source: '/',
        destination: '/en/',
        permanent: false,
      },
    ];
  },
});
