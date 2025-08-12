'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function NotFound() {
  const { lang } = useParams<{ lang: string }>();

  return (
    <div style={{ textAlign: 'center', padding: '3rem' }}>
      <h1>😢 페이지를 찾을 수 없습니다.</h1>
      <p>요청하신 페이지가 존재하지 않아요.</p>
      <div style={{ marginTop: '1rem' }}>
        <Link href={`/${lang}/`}>🏠 홈으로 돌아가기</Link>
      </div>
    </div>
  );
}
