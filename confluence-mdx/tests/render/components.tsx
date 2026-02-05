/**
 * MDX Components for rendering tests
 *
 * Callout is a simplified test version for stable HTML output.
 * Badge is imported from the actual source to avoid code duplication.
 */
import type { FC, ReactNode } from 'react'
import Badge from '@/components/badge'

/**
 * Callout component - simplified version for testing
 * (nextra/components Callout has complex dependencies)
 */
type CalloutType = 'info' | 'warning' | 'error' | 'important' | 'default'

export const Callout: FC<{
  type?: CalloutType
  children: ReactNode
}> = ({ type = 'default', children }) => {
  return (
    <div className={`callout callout-${type}`} data-type={type}>
      {children}
    </div>
  )
}

/**
 * MDX Components map for use with MDX renderer
 */
export const mdxComponents = {
  Callout,
  Badge,
}
