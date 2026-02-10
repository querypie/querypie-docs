/* eslint-env node */
import { Footer, Layout, Navbar } from 'nextra-theme-docs';
import { Head } from 'nextra/components';
import { getPageMap } from 'nextra/page-map';
import { GoogleAnalytics } from '@next/third-parties/google';
import '../globals.css';
import { Metadata } from 'next';
import React from 'react';
import { LastUpdated } from '@/components/last-updated';
import LanguageSelector2 from "@/components/language-selector2";
import ConfluenceSourceLink from "@/components/confluence-source-link";
import { QueryPieLogo } from '@/components/querypie-logo';

const defaultMetadata: Metadata = {
  title: {
    default: 'QueryPie ACP',
    template: '%s - QueryPie ACP',
  },
  description: 'QueryPie ACP',
  applicationName: 'QueryPie ACP',
  appleWebApp: {
    title: 'QueryPie ACP',
  },
  other: {
    'msapplication-TileImage': '/icon-256.png',
    'msapplication-TileColor': '#fff',
  },
};

export const metadata: Metadata =
  process.env.DEPLOYMENT_ENV !== 'production'
    ? defaultMetadata
    : {
        ...defaultMetadata,
        metadataBase: new URL('https://docs.querypie.com'),
        twitter: {
          site: 'https://docs.querypie.com',
        },
        other: {
          'msapplication-TileImage': '/icon-256.png',
          'msapplication-TileColor': '#fff',
          'naver-site-verification': process.env.NEXT_PUBLIC_NAVER_SITE_VERIFICATION_KEY as string,
        },
      };

export default async function RootLayout({ children, params }) {
  const { lang, mdxPath: _mdxPath } = await params;

  const navbar = (
    <Navbar
      logo={<QueryPieLogo />}
      logoLink={`/${lang}/`}
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
          pageMap={pageMap}
          navbar={navbar}
          footer={<Footer>{new Date().getFullYear()} &copy; QueryPie, Inc.</Footer>}
          docsRepositoryBase="https://github.com/querypie/querypie-docs/blob/main"
          editLink="Edit this page on GitHub"
          feedback={{
            content: 'Question? Give us feedback',
            labels: 'feedback',
          }}
          i18n={[
            { locale: 'en', name: 'English' },
            { locale: 'ja', name: '日本語' },
            { locale: 'ko', name: '한국어' },
          ]}
          sidebar={{ defaultMenuCollapseLevel: 1 }}
          toc={{
            title: (
              <>
                <LanguageSelector2/>
                <ConfluenceSourceLink/>
                <p>On This Page</p>
              </>
            ),
          }}
          lastUpdated={<LastUpdated locale={lang} />}
        >
          {children}
        </Layout>
      </body>
    </html>
  );
}
