/* eslint-env node */
import { Footer, Layout, Navbar } from 'nextra-theme-docs';
import { Head } from 'nextra/components';
import { getPageMap } from 'nextra/page-map';
import { GoogleAnalytics } from '@next/third-parties/google';
import '../globals.css';
import { Metadata } from 'next';
import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';
import React from 'react';
import CustomTocLayout from '@/components/custom-toc-layout';

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

// Extract layout information from Front Matter of an MDX file
function getLayoutFromMdx(mdxPath: string[], lang: string): string {
  const normalizedMdxPath = mdxPath && mdxPath.length > 0 ? mdxPath : ['index'];

  try {
    const contentPath = path.join(process.cwd(), 'src', 'content', lang, ...normalizedMdxPath) + '.mdx';

    if (!fs.existsSync(contentPath)) {
      return 'default';
    }

    const fileContent = fs.readFileSync(contentPath, 'utf-8');
    const { data } = matter(fileContent);

    return data.layout || 'default';
  } catch (error) {
    console.warn(`Failed to parse frontmatter for ${normalizedMdxPath.join('/')}:`, error);
    return 'default';
  }
}

export default async function RootLayout({ children, params }) {
  const { lang, mdxPath } = await params;

  const layoutName = getLayoutFromMdx(mdxPath, lang);
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
    />
  );

  const pageMap = await getPageMap(`/${lang || 'en'}`);

  if (layoutName === 'main-layout') {
    return (
      <html lang={lang} dir="ltr" suppressHydrationWarning>
        <Head faviconGlyph="✦" />
        {process.env.DEPLOYMENT_ENV === 'production' && process.env.NEXT_PUBLIC_GA_ID && (
          <GoogleAnalytics gaId={process.env.NEXT_PUBLIC_GA_ID} />
        )}
        <body>
          <CustomTocLayout
            pageMap={pageMap}
            navbar={navbar}
            footer={<Footer>{new Date().getFullYear()} &copy; QueryPie, Inc.</Footer>}
            docsRepositoryBase="https://github.com/chequer-io/querypie-docs/blob/main"
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
              // TODO(JK): For debugging only. Remote this later.
              extraContent: (
                <div>
                  <small>layout={layoutName}</small>
                </div>
              ),
            }}
          >
            {children}
          </CustomTocLayout>
        </body>
      </html>
    );
  } else {
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
            docsRepositoryBase="https://github.com/chequer-io/querypie-docs/blob/main"
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
              // TODO(JK): For debugging only. Remote this later.
              extraContent: (
                <div>
                  <small>layout={layoutName}</small>
                </div>
              ),
            }}
          >
            {children}
          </Layout>
        </body>
      </html>
    );
  }
}
