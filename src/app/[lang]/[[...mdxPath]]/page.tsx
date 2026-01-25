import { importPage } from 'nextra/pages';
import { useMDXComponents as getMDXComponents } from '@/mdx-components';
import { Metadata } from 'next';
import fs from 'fs';
import path from 'path';
import { getCanonicalUrl } from '@/lib/get-canonical-url';
import { extractDescriptionFromMdx } from '@/lib/extract-description';

export async function generateStaticParams() {
  const locales = ['en', 'ja', 'ko']; // Same as next.config.mjs
  const basePath = path.resolve('src', 'content'); // Content folder base path

  const paramsList: { lang: string; mdxPath: string[] }[] = [];

  // Function to find .mdx files in specific folders
  function findMdxFiles(dir: string): string[][] {
    const mdxFiles: string[][] = [];
    const files = fs.readdirSync(dir, { withFileTypes: true });

    for (const file of files) {
      const filePath = path.join(dir, file.name);

      if (file.isDirectory()) {
        // Recursively search subdirectories
        mdxFiles.push(...findMdxFiles(filePath));
      } else if (file.isFile() && file.name.endsWith('.mdx')) {
        // Collect only .mdx files
        const relativePath = path.relative(basePath, filePath);
        const pathSegments = relativePath
          .split(path.sep) // Split path
          .slice(1) // Remove locale path
          .map(
            (segment, index, arr) => (index === arr.length - 1 ? path.parse(segment).name : segment), // Remove .mdx from last element
          )
          .filter(segment => segment !== 'index');

        mdxFiles.push(pathSegments);
      }
    }

    return mdxFiles;
  }

  // Search mdx files by locale
  for (const locale of locales) {
    const localeDir = path.join(basePath, locale);
    if (fs.existsSync(localeDir)) {
      const mdxFiles = findMdxFiles(localeDir);

      for (const pathSegments of mdxFiles) {
        const fullPath = path.join(localeDir, ...pathSegments) + '.mdx';

        if (fs.existsSync(fullPath)) {
          paramsList.push({
            lang: locale,
            mdxPath: pathSegments || [], // Set mdx file path
          });
        }
      }
    }
  }

  return paramsList;
}

export async function generateMetadata(props: {
  params: Promise<{ lang: string; mdxPath: string[] }>;
}): Promise<Metadata> {
  const params = await props.params;
  const { metadata } = await importPage(params.mdxPath, params.lang || 'en');

  // Generate canonical URL
  const canonicalUrl = await getCanonicalUrl(params);

  // Generate OG image URL with query parameters
  const title = metadata.title ? encodeURIComponent(String(metadata.title)) : '';
  const description = metadata.description
    ? encodeURIComponent(String(metadata.description))
    : encodeURIComponent(extractDescriptionFromMdx(params.mdxPath, params.lang));
  const ogImagePath = `/api/og?lang=${params.lang}&title=${title}&description=${description}`;

  // Add canonical URL and OG image to metadata
  return {
    ...metadata,
    alternates: {
      ...metadata.alternates,
      canonical: canonicalUrl,
    },
    openGraph: {
      ...metadata.openGraph,
      images: [
        {
          url: ogImagePath,
          width: 1200,
          height: 630,
          alt: metadata.title ? String(metadata.title) : 'QueryPie Documentation',
        },
      ],
    },
    twitter: {
      ...metadata.twitter,
      card: 'summary_large_image',
      images: [ogImagePath],
    },
  };
}

const Wrapper = getMDXComponents().wrapper;

export default async function Page(props: {
  params: Promise<{ lang: string; mdxPath: string[] }>;
}) {
  const params = await props.params;
  const result = await importPage(params.mdxPath, params.lang || 'en');
  const { default: MDXContent, toc, metadata } = result;
  return (
    <Wrapper toc={toc} metadata={metadata}>
      <MDXContent {...props} params={params} />
    </Wrapper>
  );
}
