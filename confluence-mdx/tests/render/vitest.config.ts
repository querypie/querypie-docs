import { defineConfig } from 'vitest/config'
import { resolve } from 'path'

export default defineConfig({
  test: {
    include: ['confluence-mdx/tests/render/**/*.test.ts'],
    globals: true,
    testTimeout: 30000, // MDX compilation can be slow
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, '../../../src'),
    },
  },
})
