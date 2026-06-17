import type { Metadata } from 'next';
import { DocsSpotlightSidebar } from '@/components/docs-spotlight-sidebar';
import styles from './internal-page.module.css';

type InternalPageParams = {
  lang: string;
};

type InternalPageProps = {
  params?: Promise<InternalPageParams | undefined>;
};

type InternalPageCopy = {
  description: string;
  title: string;
};

const internalPageCopy: Record<string, InternalPageCopy> = {
  en: {
    description: 'A list of internal component and page examples maintained for review and implementation reference.',
    title: 'Internal Pages',
  },
  ja: {
    description: 'レビューと実装参考のために維持している内部コンポーネントおよびページ例の一覧です。',
    title: '内部ページ',
  },
  ko: {
    description: '검토와 구현 참고를 위해 유지 중인 내부 컴포넌트 및 페이지 예시 목록입니다.',
    title: '내부 페이지',
  },
};

const locales = Object.keys(internalPageCopy);

function getInternalPageCopy(lang: string) {
  return internalPageCopy[lang] ?? internalPageCopy.en;
}

async function getInternalPageLang(params: InternalPageProps['params']) {
  const resolvedParams = await params;

  return resolvedParams?.lang ?? 'en';
}

export function generateStaticParams() {
  return locales.map(lang => ({ lang }));
}

export async function generateMetadata({ params }: InternalPageProps): Promise<Metadata> {
  const lang = await getInternalPageLang(params);
  const copy = getInternalPageCopy(lang);

  return {
    description: copy.description,
    title: copy.title,
  };
}

export default async function InternalPage({ params }: InternalPageProps) {
  const lang = await getInternalPageLang(params);
  const copy = getInternalPageCopy(lang);

  return (
    <section
      style={{
        margin: '0 auto',
        maxWidth: '768px',
        padding: '64px 24px',
      }}
    >
      <div className={styles.internalPreviewGrid}>
        <div>
          <h1
            style={{
              color: '#111318',
              fontSize: '36px',
              fontWeight: 700,
              letterSpacing: '0',
              lineHeight: 1.2,
              margin: '0 0 16px',
            }}
          >
            {copy.title}
          </h1>
          <p
            style={{
              color: '#454a53',
              fontSize: '17px',
              letterSpacing: '0',
              lineHeight: 1.7,
              margin: 0,
            }}
          >
            {copy.description}
          </p>
        </div>
        <DocsSpotlightSidebar locale={lang} />
      </div>
    </section>
  );
}
