'use client';

import { NotFoundPage } from 'nextra-theme-docs'
import {useParams} from "next/navigation";

export default function NotFound() {
  const params = useParams<{ lang: string }>();
  const lang = params?.lang;

  if (lang === 'ko') {
    return (
      <NotFoundPage content="Submit an issue" labels="broken-link">
        <h1>페이지를 찾을 수 없습니다.</h1>
      </NotFoundPage>
    )
  } else if (lang === 'ja') {
    return (
      <NotFoundPage content="Submit an issue" labels="broken-link">
        <h1>申し訳ありません。ページが見つかりませんでした。</h1>
      </NotFoundPage>
    )
  } else {
    return (
      <NotFoundPage content="Submit an issue" labels="broken-link">
        <h1>Sorry, we could not find that page.</h1>
      </NotFoundPage>
    )
  }
}
