import fs from 'fs';
import path from 'path';

/**
 * MDX 파일 본문에서 description을 추출합니다.
 *
 * 추출 규칙:
 * 1. Frontmatter 제거
 * 2. Import 문 제거
 * 3. 모든 heading 제거 (#, ##, ### 등)
 * 4. JSX/HTML 태그 제거
 * 5. 첫 번째 의미있는 텍스트 추출 (maxLength 이내)
 */
export function extractDescriptionFromMdx(
  mdxPath: string[],
  lang: string,
  maxLength: number = 300
): string {
  const basePath = path.resolve('src', 'content');
  let filePath = path.join(basePath, lang, ...mdxPath) + '.mdx';

  // 파일이 없으면 index.mdx 시도
  if (!fs.existsSync(filePath)) {
    const indexPath = path.join(basePath, lang, ...mdxPath, 'index.mdx');
    if (fs.existsSync(indexPath)) {
      filePath = indexPath;
    } else {
      return '';
    }
  }

  const content = fs.readFileSync(filePath, 'utf-8');

  // 1. Frontmatter 제거
  let text = content.replace(/^---[\s\S]*?---\n*/m, '');

  // 2. Import 문 제거
  text = text.replace(/^import\s+.*$/gm, '');

  // 3. 모든 heading 제거 (#, ##, ### 등)
  text = text.replace(/^#{1,6}\s+.+$/gm, '');

  // 4. JSX/HTML 태그 제거 (멀티라인 포함)
  // Self-closing 태그
  text = text.replace(/<[^>]+\/>/g, '');
  // 블록 태그 (Callout, figure 등)
  text = text.replace(/<(\w+)[^>]*>[\s\S]*?<\/\1>/g, '');
  // 남은 태그
  text = text.replace(/<[^>]+>/g, '');

  // 5. Markdown 이미지 제거
  text = text.replace(/!\[[^\]]*\]\([^)]+\)/g, '');

  // 6. Markdown 링크는 텍스트만 유지
  text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

  // 7. Bold, Italic, Code 마커 제거하되 텍스트는 유지
  text = text.replace(/\*\*([^*]+)\*\*/g, '$1');
  text = text.replace(/\*([^*]+)\*/g, '$1');
  text = text.replace(/`([^`]+)`/g, '$1');

  // 8. 리스트 마커 제거
  text = text.replace(/^[\s]*[-*]\s+/gm, '');
  text = text.replace(/^[\s]*\d+\.\s+/gm, '');

  // 9. 여러 줄바꿈을 하나로, 공백 정리
  text = text.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();

  // 10. 빈 문자열이면 반환
  if (!text) {
    return '';
  }

  // 11. maxLength 이내로 truncate (OG 이미지에서 CSS line-clamp로 처리하므로 여유있게 설정)
  if (text.length <= maxLength) {
    return text;
  }

  return text.substring(0, maxLength);
}
