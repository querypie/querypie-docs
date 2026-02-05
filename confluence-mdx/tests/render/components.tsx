/**
 * MDX Components for rendering tests
 *
 * These are simplified versions of the actual Nextra components,
 * designed to produce consistent HTML output for snapshot testing.
 */
import type { FC, ReactNode } from 'react'

/**
 * Callout component - matches nextra/components Callout
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
 * Badge component - matches custom Badge from src/components/badge.tsx
 */
type BadgeColor = 'grey' | 'blue' | 'green' | 'yellow' | 'red' | 'purple'

const badgeColorStyles: Record<BadgeColor, { background: string; color: string }> = {
  grey: { background: '#DDDEE1', color: '#292A2E' },
  blue: { background: '#8FB8F6', color: '#292A2E' },
  green: { background: '#B3DF72', color: '#292A2E' },
  yellow: { background: '#F9C84E', color: '#292A2E' },
  red: { background: '#FD9891', color: '#292A2E' },
  purple: { background: '#D8A0F7', color: '#292A2E' },
}

export const Badge: FC<{
  color?: BadgeColor
  children: ReactNode
}> = ({ color = 'grey', children }) => {
  const styles = badgeColorStyles[color] || badgeColorStyles.grey

  return (
    <span
      className="badge"
      data-color={color}
      style={{
        display: 'inline-block',
        padding: '2px 5px 2px 4px',
        margin: '0 2px',
        borderRadius: '3px',
        fontSize: '0.75em',
        fontWeight: 700,
        lineHeight: 1.1,
        letterSpacing: '-0.3px',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
        position: 'relative',
        top: '-1px',
        backgroundColor: styles.background,
        color: styles.color,
      }}
    >
      {children}
    </span>
  )
}

/**
 * MDX Components map for use with MDX renderer
 */
export const mdxComponents = {
  Callout,
  Badge,
}
