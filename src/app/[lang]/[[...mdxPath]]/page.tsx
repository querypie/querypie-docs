import { importPage } from 'nextra/pages';
import { useMDXComponents as getMDXComponents } from '@/mdx-components';
import fs from 'fs';
import path from 'path';

export async function generateStaticParams() {
  const locales = ['en', 'ko', 'ja']; // next.config.mjs와 동일
  const basePath = path.resolve('src', 'content'); // content 폴더 기준

  const paramsList: { lang: string; mdxPath: string[] }[] = [];

  // 특정 폴더 내 .mdx 파일을 찾는 함수
  function findMdxFiles(dir: string): string[][] {
    const mdxFiles: string[][] = [];
    const files = fs.readdirSync(dir, { withFileTypes: true });

    for (const file of files) {
      const filePath = path.join(dir, file.name);

      if (file.isDirectory()) {
        // 하위 디렉토리를 재귀적으로 탐색
        mdxFiles.push(...findMdxFiles(filePath));
      } else if (file.isFile() && file.name.endsWith('.mdx')) {
        // .mdx 파일만 수집
        const relativePath = path.relative(basePath, filePath);
        const pathSegments = relativePath
          .split(path.sep) // 경로를 분할
          .slice(1) // locale 경로 제거
          .map(
            (segment, index, arr) => (index === arr.length - 1 ? path.parse(segment).name : segment), // 마지막 엘리먼트에서 .mdx 제거
          )
          .filter(segment => segment !== 'index');

        mdxFiles.push(pathSegments);
      }
    }

    return mdxFiles;
  }

  // 로케일별로 mdx 파일 검색
  for (const locale of locales) {
    const localeDir = path.join(basePath, locale);
    if (fs.existsSync(localeDir)) {
      const mdxFiles = findMdxFiles(localeDir);

      for (const pathSegments of mdxFiles) {
        const fullPath = path.join(localeDir, ...pathSegments) + '.mdx';

        if (fs.existsSync(fullPath)) {
          paramsList.push({
            lang: locale,
            mdxPath: pathSegments || [], // mdx 파일 경로 설정
          });
        }
      }
    }
  }

  return paramsList;
}

export async function generateMetadata(props) {
  const params = await props.params;
  const { metadata } = await importPage(params.mdxPath, params.lang || 'en');
  return metadata;
}

const Wrapper = getMDXComponents().wrapper;

export default async function Page(props) {
  const params = await props.params;
  const result = await importPage(params.mdxPath, params.lang || 'en');
  const { default: MDXContent, toc, metadata } = result;
  return (
    <Wrapper toc={toc} metadata={metadata}>
      <MDXContent {...props} params={params} />
    </Wrapper>
  );
}
