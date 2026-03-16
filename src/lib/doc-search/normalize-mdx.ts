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

function stripImports(content: string): string {
  return content
    .split('\n')
    .filter(line => !line.trim().startsWith('import '))
    .join('\n');
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
  const strippedImports = stripImports(parsed.content);
  const withImageAlt = replaceImageTags(strippedImports);
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
