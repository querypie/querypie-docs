import { describe, expect, it } from 'vitest';

import { normalizeMdxForLLM, extractTableOfContents } from '@/lib/doc-search/normalize-mdx';

// ---------------------------------------------------------------------------
// 공통 픽스처
// ---------------------------------------------------------------------------

/** Callout 컴포넌트를 import하고 코드 블록 안에도 import가 있는 MDX */
const MDX_WITH_CALLOUT_AND_CODE_IMPORTS = `---
title: 파이썬 환경 설정 가이드
description: Python 개발 환경 구성 방법
---

import { Callout } from 'nextra/components'
import { Steps } from 'nextra/components'

# 파이썬 환경 설정 가이드

## 사전 요구사항

<Callout type="warning">
Python 3.10 이상이 필요합니다. 설치 전 버전을 확인하세요.
</Callout>

## 패키지 설치

아래 명령어로 의존성을 설치합니다:

\`\`\`python
import pandas as pd
import numpy as np

df = pd.DataFrame({'col': [1, 2, 3]})
print(df)
\`\`\`

## 데이터 저장

분석 결과를 파일로 저장합니다:

\`\`\`python
# CSV로 저장
import csv

with open('output.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['a', 'b'])
\`\`\`

## 완료

환경 설정이 완료되었습니다.
`;

/** 기본 Callout + 이미지 MDX (기존 테스트용) */
const MDX_BASIC = `---
title: Monitoring
---

import { Callout } from 'nextra/components'

# Monitoring

### Overview

<Callout type="info">
10.3.0부터 Audit의 하위 항목으로 모니터링만 가능했던 Running Queries 기능에 쿼리 강제 중지 기능이 추가되었습니다.
</Callout>

<figure>
<img src="/foo.png" alt="Running Queries 화면" />
<figcaption>Running Queries 화면</figcaption>
</figure>
`;

// ---------------------------------------------------------------------------
// normalizeMdxForLLM
// ---------------------------------------------------------------------------

describe('normalizeMdxForLLM — 기본 동작', () => {
  it('frontmatter와 MDX import를 제거하고 본문 텍스트를 유지합니다', () => {
    const result = normalizeMdxForLLM(MDX_BASIC);

    expect(result).not.toContain('import { Callout }');
    expect(result).not.toContain('---');
    expect(result).toContain(
      '10.3.0부터 Audit의 하위 항목으로 모니터링만 가능했던 Running Queries 기능에 쿼리 강제 중지 기능이 추가되었습니다.',
    );
    expect(result).toContain('Running Queries 화면');
  });
});

describe('normalizeMdxForLLM — MDX 컴포넌트 import 제거', () => {
  /**
   * MDX 파일 최상위에 선언된 컴포넌트 import 구문은 검색 인덱스와 LLM 페이로드에
   * 필요 없으므로 제거되어야 합니다.
   *
   * 수정 전 동작 (버그):
   *   stripFencedCodeBlocks 없이 stripImports만 실행되면,
   *   코드 블록 안의 `import pandas as pd` 같은 줄도 함께 삭제됩니다.
   *
   * 수정 후 동작:
   *   stripFencedCodeBlocks → stripImports 순서로 실행되어
   *   MDX 최상위 import만 제거되고 코드 블록은 이미 통째로 제거된 상태입니다.
   */
  it('단일 컴포넌트 import 구문을 제거합니다', () => {
    const source = `
import { Callout } from 'nextra/components'

# 제목

본문 텍스트입니다.
`.trim();

    const result = normalizeMdxForLLM(source);

    expect(result).not.toContain("import { Callout }");
    expect(result).toContain('# 제목');
    expect(result).toContain('본문 텍스트입니다.');
  });

  it('여러 컴포넌트 import 구문을 모두 제거합니다', () => {
    const source = `
import { Callout } from 'nextra/components'
import { Steps, Tabs, Tab } from 'nextra/components'
import { CustomTable } from '@/components/CustomTable'

# 제목

본문입니다.
`.trim();

    const result = normalizeMdxForLLM(source);

    expect(result).not.toContain("import { Callout }");
    expect(result).not.toContain("import { Steps");
    expect(result).not.toContain("import { CustomTable }");
    expect(result).toContain('# 제목');
    expect(result).toContain('본문입니다.');
  });
});

describe('normalizeMdxForLLM — MDX import와 코드 블록 내 import 분리', () => {
  /**
   * MDX 파일에는 두 종류의 import가 공존할 수 있습니다:
   *
   *   1. MDX 최상위 import  — 컴포넌트 선언
   *      import { Callout } from 'nextra/components'
   *      → processFenceAware()가 펜스 외부 라인에서 제거
   *
   *   2. 코드 블록 내부 import — 예시 코드의 일부
   *      ```python
   *      import pandas as pd   ← 이것은 코드 예시
   *      ```
   *      → 코드 블록 내용을 유지하므로 검색 색인에 포함됨
   *
   * processFenceAware가 펜스 내부/외부를 구분해 올바르게 처리하는지 검증합니다.
   */
  it('MDX import는 제거하고 코드 블록 내 import는 검색 가능하게 유지합니다', () => {
    const result = normalizeMdxForLLM(MDX_WITH_CALLOUT_AND_CODE_IMPORTS);

    // MDX 최상위 import는 processFenceAware가 펜스 외부에서 제거합니다
    expect(result).not.toContain("import { Callout }");
    expect(result).not.toContain("import { Steps }");

    // 코드 블록 내부의 import는 코드 예시의 일부로 검색 색인에 포함됩니다
    expect(result).toContain('import pandas as pd');
    expect(result).toContain('import numpy as np');
    expect(result).toContain('import csv');

    // 코드 블록 내용(코드 자체)도 검색 가능하도록 유지됩니다
    expect(result).toContain('pd.DataFrame');
    expect(result).toContain("csv.writer");
  });

  it('Callout 태그는 제거되지만 Callout 내부 텍스트는 검색 가능하도록 유지됩니다', () => {
    const result = normalizeMdxForLLM(MDX_WITH_CALLOUT_AND_CODE_IMPORTS);

    // Callout 컴포넌트 태그 자체는 제거됩니다
    expect(result).not.toContain('<Callout');
    expect(result).not.toContain('</Callout>');

    // Callout 안의 텍스트는 검색 인덱스를 위해 유지됩니다
    expect(result).toContain('Python 3.10 이상이 필요합니다. 설치 전 버전을 확인하세요.');
  });

  it('코드 블록과 import를 제거한 뒤 일반 섹션 헤딩과 본문은 유지됩니다', () => {
    const result = normalizeMdxForLLM(MDX_WITH_CALLOUT_AND_CODE_IMPORTS);

    // 헤딩은 유지됩니다
    expect(result).toContain('## 사전 요구사항');
    expect(result).toContain('## 패키지 설치');
    expect(result).toContain('## 데이터 저장');
    expect(result).toContain('## 완료');

    // 코드 블록 밖의 일반 본문은 유지됩니다
    expect(result).toContain('아래 명령어로 의존성을 설치합니다');
    expect(result).toContain('분석 결과를 파일로 저장합니다');
    expect(result).toContain('환경 설정이 완료되었습니다.');
  });
});

// ---------------------------------------------------------------------------
// extractTableOfContents
// ---------------------------------------------------------------------------

describe('extractTableOfContents — 기본 동작', () => {
  it('소스 순서대로 헤딩 레이블을 반환합니다', () => {
    expect(extractTableOfContents(MDX_BASIC)).toEqual(['Monitoring', 'Overview']);
  });
});

describe('extractTableOfContents — 코드 블록 내 # 주석 제외', () => {
  /**
   * 수정 전 동작 (버그):
   *   코드 블록 안의 `# CSV로 저장` 같은 줄이 헤딩으로 오인되어
   *   tableOfContents에 포함됩니다.
   *   terminal-sandbox.mdx 등 코드 예시가 많은 문서에서 실제로 발생했습니다.
   *
   * 수정 후 동작:
   *   stripFencedCodeBlocks가 코드 블록을 먼저 제거하므로
   *   코드 내부의 # 주석은 헤딩 감지 대상에서 제외됩니다.
   */
  it('코드 블록 안의 셸 주석(# comment)을 TOC 헤딩으로 인식하지 않습니다', () => {
    // 실제 MDX 헤딩과 코드 블록 주석의 텍스트를 의도적으로 다르게 구성합니다.
    // 수정 전 버그: terminal-sandbox.mdx 같은 파일에서 코드 안의
    //   `# 데이터 생성`, `# CSV로 저장`, `# 로그 파일 생성` 이
    //   실제 헤딩처럼 TOC에 추가되었습니다.
    const source = `
# 데이터 처리 가이드

## 스크립트 실행

아래 스크립트를 순서대로 실행합니다:

\`\`\`bash
# 데이터 생성
python generate.py

# CSV로 저장
python save.py

# 로그 파일 생성
python log.py
\`\`\`

## 결과 확인

출력 파일을 확인합니다.
`.trim();

    const toc = extractTableOfContents(source);

    // 실제 문서 헤딩만 포함됩니다
    expect(toc).toContain('데이터 처리 가이드');
    expect(toc).toContain('스크립트 실행');
    expect(toc).toContain('결과 확인');

    // 수정 전에는 이 항목들이 TOC에 잘못 포함되었습니다
    expect(toc).not.toContain('데이터 생성');
    expect(toc).not.toContain('CSV로 저장');
    expect(toc).not.toContain('로그 파일 생성');
  });

  it('코드 블록 밖의 정상 헤딩은 모두 TOC에 포함됩니다', () => {
    const toc = extractTableOfContents(MDX_WITH_CALLOUT_AND_CODE_IMPORTS);

    expect(toc).toContain('파이썬 환경 설정 가이드');
    expect(toc).toContain('사전 요구사항');
    expect(toc).toContain('패키지 설치');
    expect(toc).toContain('데이터 저장');
    expect(toc).toContain('완료');

    // 코드 블록 안의 `# CSV로 저장` 주석은 TOC에 없습니다
    expect(toc).not.toContain('CSV로 저장');
  });
});
