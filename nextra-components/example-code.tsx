import fs from 'node:fs/promises'
import path from 'node:path'
import { compileMdx } from 'nextra/compile'
import type { FC } from 'react'
import { MDXRemote } from 'nextra/mdx-remote'

export const ExampleCode: FC<{
  filePath: string
  metadata: string
  example: string
}> = async ({ filePath, metadata, example }) => {
  // Example middleware code for i18n
  const exampleCode = `import { createI18nMiddleware } from 'nextra/locales'

const I18nMiddleware = createI18nMiddleware({
  locales: ['en', 'zh', 'de'],
  defaultLocale: 'en'
})

export default I18nMiddleware

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)']
}`

  const ext = path.extname(filePath).slice(1)

  const rawJs = await compileMdx(
    `~~~${ext} filename="${filePath}" showLineNumbers ${metadata}
${exampleCode}
~~~`,
    { defaultShowCopyCode: true }
  )
  return <MDXRemote compiledSource={rawJs} />
}
