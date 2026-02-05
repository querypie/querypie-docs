/**
 * MDX to HTML Renderer for testing
 *
 * Compiles MDX content to HTML using @mdx-js/mdx and React DOM server rendering.
 */
import { compile, run } from '@mdx-js/mdx'
import * as runtime from 'react/jsx-runtime'
import { renderToStaticMarkup } from 'react-dom/server'
import { mdxComponents } from './components'

/**
 * Remove frontmatter (YAML block between ---) from MDX content
 */
function removeFrontmatter(content: string): string {
  const frontmatterRegex = /^---\n[\s\S]*?\n---\n*/
  return content.replace(frontmatterRegex, '')
}

/**
 * Remove import statements from MDX content
 * The components are injected via the components prop instead
 */
function removeImports(content: string): string {
  const importRegex = /^import\s+.*?(?:from\s+['"].*?['"])?;?\s*$/gm
  return content.replace(importRegex, '')
}

/**
 * Format HTML for consistent comparison
 * - Add newlines after block elements
 * - Normalize whitespace
 */
function formatHtml(html: string): string {
  // Add newlines after closing block tags for readability
  const blockTags = ['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'table', 'tr', 'thead', 'tbody', 'figure', 'figcaption', 'pre', 'blockquote']
  let formatted = html

  for (const tag of blockTags) {
    formatted = formatted.replace(new RegExp(`(</${tag}>)`, 'gi'), `$1\n`)
  }

  // Remove multiple consecutive newlines
  formatted = formatted.replace(/\n{3,}/g, '\n\n')

  // Trim leading/trailing whitespace
  return formatted.trim() + '\n'
}

/**
 * Render MDX content to HTML string
 *
 * @param mdxContent - Raw MDX file content (including frontmatter)
 * @returns Rendered HTML string
 */
export async function renderMdxToHtml(mdxContent: string): Promise<string> {
  // 1. Remove frontmatter and imports
  let processedContent = removeFrontmatter(mdxContent)
  processedContent = removeImports(processedContent)

  // 2. Compile MDX to JavaScript
  const compiled = await compile(processedContent, {
    outputFormat: 'function-body',
    development: false,
    // Skip JSX validation for simpler output
    jsx: false,
  })

  // 3. Run the compiled code to get React component
  const { default: MDXContent } = await run(compiled, {
    ...runtime,
    baseUrl: import.meta.url,
  })

  // 4. Render React component to static HTML
  const html = renderToStaticMarkup(
    MDXContent({ components: mdxComponents })
  )

  // 5. Format HTML for consistent comparison
  return formatHtml(html)
}

/**
 * Compare two HTML strings, ignoring whitespace differences
 */
export function compareHtml(actual: string, expected: string): boolean {
  const normalizeWhitespace = (s: string) =>
    s.replace(/\s+/g, ' ').replace(/>\s+</g, '><').trim()

  return normalizeWhitespace(actual) === normalizeWhitespace(expected)
}
