# 콘텐츠 구조 및 파일 위치 안내

## 핵심 요약

**콘텐츠 파일의 단일 진실 공급원(Source of Truth)은 `src/content/`입니다.**

`confluence-mdx/target/{ko,en,ja}/`는 `src/content/{ko,en,ja}/`를 가리키는 **심볼릭 링크**입니다.
두 경로는 동일한 파일을 참조하므로 어느 쪽에서 열어도 같은 파일입니다.

```
confluence-mdx/target/ko  →  ../../src/content/ko  (심볼릭 링크)
confluence-mdx/target/en  →  ../../src/content/en
confluence-mdx/target/ja  →  ../../src/content/ja
confluence-mdx/target/public  →  ../../public
```

## 작업 경로 선택 기준

| 작업 | 사용 경로 | 이유 |
|------|-----------|------|
| 콘텐츠 파일 편집 | `src/content/{lang}/...` | Source of Truth |
| Skeleton MDX 비교 | `confluence-mdx/target/ko/...` | cli.py가 `target/{lang}/` 경로 형식을 요구함 |
| 이미지 추가 | `public/...` | |

## Skeleton MDX 비교 경로 규칙

`confluence-mdx/bin/skeleton/cli.py`는 입력 경로에서 `target/{lang}/` 패턴을 파싱하여
대응하는 `target/en/`, `target/ja/` 파일을 자동으로 찾습니다.

```bash
# ✅ 올바른 사용법 — target/ko/ 경로 사용
cd confluence-mdx
python3 bin/skeleton/cli.py target/ko/installation/some-page.mdx

# ❌ 작동하지 않음 — src/content 경로는 인식 불가
python3 bin/skeleton/cli.py ../src/content/ko/installation/some-page.mdx
# WARNING: Corresponding Korean MDX file not found: ...
```

`target/ko/`와 `src/content/ko/`는 **동일한 파일**이므로,
`target/ko/` 경로로 Skeleton 비교를 실행하면 현재 `src/content/`의 내용이 비교됩니다.

## 심볼릭 링크 존재 이유

`confluence-mdx/`의 변환기(fetch_cli.py)가 `target/ko/`에 파일을 출력하면,
심볼릭 링크를 통해 실제로는 `src/content/ko/`에 저장됩니다.

```
Confluence API → fetch_cli.py → target/ko/ (심볼릭 링크) → src/content/ko/
```

## 디렉토리 구조 참고

```
querypie-docs/
├── src/content/          ← 콘텐츠 파일 실제 위치 (Source of Truth)
│   ├── ko/
│   ├── en/
│   └── ja/
├── public/               ← 공용 이미지
└── confluence-mdx/
    └── target/           ← 심볼릭 링크만 존재 (실제 파일 없음)
        ├── ko → ../../src/content/ko
        ├── en → ../../src/content/en
        ├── ja → ../../src/content/ja
        └── public → ../../public
```
