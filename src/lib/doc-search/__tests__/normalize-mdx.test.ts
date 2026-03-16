import { describe, expect, it } from 'vitest';

import { normalizeMdxForLLM, extractTableOfContents } from '@/lib/doc-search/normalize-mdx';

const sampleMdx = `---
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

describe('normalizeMdxForLLM', () => {
  it('removes frontmatter/imports but keeps useful text', () => {
    const result = normalizeMdxForLLM(sampleMdx);

    expect(result).not.toContain('import { Callout }');
    expect(result).not.toContain('---');
    expect(result).toContain('10.3.0부터 Audit의 하위 항목으로 모니터링만 가능했던 Running Queries 기능에 쿼리 강제 중지 기능이 추가되었습니다.');
    expect(result).toContain('Running Queries 화면');
  });
});

describe('extractTableOfContents', () => {
  it('returns heading labels in source order', () => {
    expect(extractTableOfContents(sampleMdx)).toEqual(['Monitoring', 'Overview']);
  });
});
