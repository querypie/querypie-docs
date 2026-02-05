/**
 * MDX Render Tests
 *
 * Tests that MDX files render to the expected HTML output.
 */
import { describe, it, expect } from 'vitest'
import * as fs from 'fs'
import * as path from 'path'
import { renderMdxToHtml } from './mdx-renderer'

const testcasesDir = path.resolve(__dirname, '../testcases')

// Get all testcase directories that have expected.mdx
function getTestCases(): string[] {
  return fs
    .readdirSync(testcasesDir)
    .filter(name => {
      const dir = path.join(testcasesDir, name)
      return (
        fs.statSync(dir).isDirectory() &&
        fs.existsSync(path.join(dir, 'expected.mdx'))
      )
    })
    .sort()
}

describe('MDX Rendering', () => {
  const testCases = getTestCases()

  it.each(testCases)('renders testcase %s correctly', async testId => {
    const testDir = path.join(testcasesDir, testId)
    const mdxPath = path.join(testDir, 'expected.mdx')
    const htmlPath = path.join(testDir, 'expected.html')
    const outputPath = path.join(testDir, 'output.html')

    // Read MDX content
    const mdxContent = fs.readFileSync(mdxPath, 'utf-8')

    // Render to HTML
    const renderedHtml = await renderMdxToHtml(mdxContent)

    // Write output for debugging
    fs.writeFileSync(outputPath, renderedHtml)

    // Check if expected.html exists
    if (!fs.existsSync(htmlPath)) {
      // If no expected.html, create it and skip comparison
      console.log(`Creating expected.html for ${testId}`)
      fs.writeFileSync(htmlPath, renderedHtml)
      return
    }

    // Compare with expected
    const expectedHtml = fs.readFileSync(htmlPath, 'utf-8')
    expect(renderedHtml).toBe(expectedHtml)
  })
})
