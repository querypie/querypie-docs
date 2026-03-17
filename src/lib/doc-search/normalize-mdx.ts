import matter from 'gray-matter';

const FRONTMATTER_SEPARATOR = /^---\s*$/m;

function decodeHtmlEntities(input: string): string {
  return input
    .replace(/&gt;/g, '>')
    .replace(/&lt;/g, '<')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function processFenceAware(content: string): string {
  const lines = content.split('\n');
  const result: string[] = [];
  let inFence = false;

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith('```')) {
      inFence = !inFence;
      // 펜스 마커 라인 자체는 출력에서 제거
      continue;
    }

    if (inFence) {
      // 코드 블록 내부: 내용을 유지하되 줄 앞의 # 을 제거해 헤딩 오인 방지
      // `# CSV로 저장` → `CSV로 저장` 으로 텍스트는 검색 대상으로 유지됨
      result.push(line.replace(/^#+\s/, ''));
    } else {
      // 코드 블록 외부: MDX 컴포넌트 import 구문만 제거
      if (!trimmed.startsWith('import ')) {
        result.push(line);
      }
    }
  }

  return result.join('\n');
}

function replaceImageTags(content: string): string {
  return content.replace(/<img[^>]*alt="([^"]+)"[^>]*\/?>(?:<\/img>)?/g, '$1');
}

function stripWrapperTags(content: string): string {
  return content
    .replace(/<Callout[^>]*>/g, '')
    .replace(/<\/Callout>/g, '')
    .replace(/<figure[^>]*>/g, '')
    .replace(/<\/figure>/g, '')
    .replace(/<figcaption[^>]*>/g, '')
    .replace(/<\/figcaption>/g, '')
    .replace(/<details[^>]*>/g, '')
    .replace(/<\/details>/g, '')
    .replace(/<summary[^>]*>/g, '')
    .replace(/<\/summary>/g, '')
    .replace(/<[^>]+>/g, ' ');
}

function normalizeWhitespace(content: string): string {
  return content
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n +/g, '\n')
    .trim();
}

export function normalizeMdxForLLM(source: string): string {
  const parsed = source.match(FRONTMATTER_SEPARATOR) ? matter(source) : { content: source };
  const processed = processFenceAware(parsed.content);
  const withImageAlt = replaceImageTags(processed);
  const withoutTags = stripWrapperTags(withImageAlt);
  return normalizeWhitespace(decodeHtmlEntities(withoutTags));
}

export function extractTableOfContents(source: string): string[] {
  const content = normalizeMdxForLLM(source);
  return content
    .split('\n')
    .filter(line => /^(#+)\s+/.test(line))
    .map(line => line.replace(/^(#+)\s+/, '').trim());
}
