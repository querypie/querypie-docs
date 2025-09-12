/* eslint-env node */
import { Footer, Layout, Navbar } from 'nextra-theme-docs';
import { Head } from 'nextra/components';
import { getPageMap } from 'nextra/page-map';
import { GoogleAnalytics } from '@next/third-parties/google';
import '../globals.css';
import { Metadata } from 'next';

export const metadata = (() => {
  const defaultMetadata: Metadata = {
    title: {
      default: 'QueryPi Docs',
      template: '%s - QueryPie Docs',
    },
    description: 'QueryPie Docs',
    applicationName: 'QueryPie Docs',
    appleWebApp: {
      title: 'QueryPie Docs',
    },
    other: {
      'msapplication-TileImage': '/icon-256.png',
      'msapplication-TileColor': '#fff',
    },
  };

  if (process.env.DEPLOYMENT_ENV !== 'production') {
    return defaultMetadata;
  }

  return {
    ...defaultMetadata,
    metadataBase: new URL('https://querypie-docs.vercel.app'),
    twitter: {
      site: 'https://querypie-docs.vercel.app',
    },
    other: {
      'msapplication-TileImage': '/icon-256.png',
      'msapplication-TileColor': '#fff',
      'naver-site-verification': process.env.NEXT_PUBLIC_NAVER_SITE_VERIFICATION_KEY as string,
    },
  };
})();

export default async function RootLayout({ children, params }) {
  const { lang } = await params;

  const navbar = (
    <Navbar
      logo={
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
            <img src="/icon-32.png" alt="QueryPie Logo" width={18} height={18} />
            <div>
              <b>QueryPie</b> <span style={{ opacity: '60%' }}>Docs</span>
            </div>
          </div>
        </div>
      }
      logoLink={`/${lang}/`}
      // // Next.js discord server
      // chatLink="https://discord.gg/hEM84NMkRv"
    />
  );

  const pageMap = await getPageMap(`/${lang || 'en'}`);

  return (
    <html lang={lang} dir="ltr" suppressHydrationWarning>
      <Head faviconGlyph="✦" />
      {process.env.DEPLOYMENT_ENV === 'production' && process.env.NEXT_PUBLIC_GA_ID && (
        <GoogleAnalytics gaId={process.env.NEXT_PUBLIC_GA_ID} />
      )}
      <body>
        <Layout
          navbar={navbar}
          footer={<Footer>{new Date().getFullYear()} &copy; QueryPie, Inc.</Footer>}
          editLink="Edit this page on GitHub"
          docsRepositoryBase="https://github.com/chequer-io/querypie-docs/blob/main"
          feedback={{
            content: '',
            labels: '',
          }}
          sidebar={{ defaultMenuCollapseLevel: 1 }}
          pageMap={pageMap}
          i18n={[
            { locale: 'en', name: 'English' },
            { locale: 'ja', name: '日本語' },
            { locale: 'ko', name: '한국어' },
          ]}
        >
          {children}
        </Layout>
      </body>
    </html>
  );
}
