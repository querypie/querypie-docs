import nextra from 'nextra';

// Set up Nextra with its configuration
const withNextra = nextra({
  latex: true,
  search: {
    codeblocks: false,
  },
  contentDirBasePath: '/',
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
  async redirects() {
    return [
      {
        source: '/',
        destination: '/en/',
        permanent: false,
      },
    ];
  },
  webpack(config) {
      // rule.exclude doesn't work starting from Next.js 15
      const { test: _test, ...imageLoaderOptions } = config.module.rules.find(
          rule => rule.test?.test?.('.svg')
      )
      config.module.rules.push({
          test: /\.svg$/,
          oneOf: [
              {
                  resourceQuery: /svgr/,
                  use: ['@svgr/webpack']
              },
              imageLoaderOptions
          ]
      })
      return config
  },
  experimental: {
      turbo: {
          rules: {
              './components/icons/*.svg': {
                  loaders: ['@svgr/webpack'],
                  as: '*.js'
              }
          }
      },
      optimizePackageImports: ['@components/icons']
  }
});
