import { load } from 'js-yaml';

export interface ParsedFrontmatter {
  data: Record<string, unknown>;
  content: string;
}

const FRONTMATTER_OPEN = /^---[ \t]*(?:\r?\n)/;
const FRONTMATTER_CLOSE = /\r?\n---[ \t]*(?:\r?\n|$)/;

export function parseFrontmatter(source: string): ParsedFrontmatter {
  if (!FRONTMATTER_OPEN.test(source)) {
    return { data: {}, content: source };
  }

  const bodyStart = source.match(FRONTMATTER_OPEN)?.[0].length ?? 0;
  const rest = source.slice(bodyStart);
  const closeMatch = rest.match(FRONTMATTER_CLOSE);

  if (!closeMatch || closeMatch.index === undefined) {
    return { data: {}, content: source };
  }

  const rawYaml = rest.slice(0, closeMatch.index);
  const rawData = load(rawYaml);
  const data = rawData && typeof rawData === 'object' && !Array.isArray(rawData) ? (rawData as Record<string, unknown>) : {};
  const content = rest.slice(closeMatch.index + closeMatch[0].length);

  return { data, content };
}
