'use client'

import { usePathname } from 'next/navigation'
import type { FC, ReactNode } from 'react'
import { useThemeConfig } from 'nextra-theme-docs'

export const LastUpdated: FC<{
  date?: Date
  children?: ReactNode
  locale?: string
}> = ({ date, children = 'Last updated on', locale = 'en' }) => {
  const { i18n } = useThemeConfig()
  const pathname = usePathname()

  if (!date) {
    return null
  }

  // Bug fix: Extract locale from pathname more safely
  let dateLocale = locale
  if (i18n.length && pathname) {
    const pathSegments = pathname.split('/').filter(Boolean) // Remove empty strings
    if (pathSegments.length > 0) {
      const firstSegment = pathSegments[0]
      // Verify if the locale exists in i18n configuration
      const validLocale = i18n.find(item => item.locale === firstSegment)
      if (validLocale) {
        dateLocale = firstSegment
      }
    }
  }

  return (
    <>
      {children}{' '}
      <time
        dateTime={date.toISOString()}
        // Can provoke React 418 error https://react.dev/errors/418
        suppressHydrationWarning
      >
        {date.toLocaleDateString(dateLocale, {
          day: 'numeric',
          month: 'long',
          year: 'numeric'
        })}
      </time>
    </>
  )
}

