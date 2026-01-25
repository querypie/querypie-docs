import type { FC, ReactNode } from 'react'

type BadgeColor = 'grey' | 'blue' | 'green' | 'yellow' | 'red' | 'purple'

const colorStyles: Record<BadgeColor, { background: string; color: string }> = {
  grey: { background: '#DDDEE1', color: '#292A2E' },
  blue: { background: '#8FB8F6', color: '#292A2E' },
  green: { background: '#B3DF72', color: '#292A2E' },
  yellow: { background: '#F9C84E', color: '#292A2E' },
  red: { background: '#FD9891', color: '#292A2E' },
  purple: { background: '#D8A0F7', color: '#292A2E' },
}

/**
 * Badge component for displaying status labels with colored backgrounds.
 * Renders as an inline element, matching Confluence's {status} macro appearance.
 *
 * @example
 * <Badge color="blue">IN PROGRESS</Badge>
 * <Badge color="green">DONE</Badge>
 * <Badge color="red">AT RISK</Badge>
 */
const Badge: FC<{
  /** The color variant of the badge */
  color?: BadgeColor
  /** The content to display inside the badge */
  children: ReactNode
}> = ({ color = 'grey', children }) => {
  const styles = colorStyles[color] || colorStyles.grey

  return (
    <span
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

export default Badge
