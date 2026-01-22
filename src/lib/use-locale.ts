'use client';

import { usePathname } from 'next/navigation';
import { useThemeConfig } from 'nextra-theme-docs';

const useLocale = (defaultLocale: string = 'en'): string => {
  const { i18n } = useThemeConfig();
  const pathname = usePathname();

  let locale = defaultLocale;
  if (i18n.length && pathname) {
    const pathSegments = pathname.split('/').filter(Boolean); // Remove empty strings

    if (pathSegments.length > 0) {
      const firstSegment = pathSegments[0];

      // Verify if the locale exists in i18n configuration
      const validLocale = i18n.find(item => item.locale === firstSegment);

      if (validLocale) {
        locale = firstSegment;
      }
    }
  }

  return locale;
};

export default useLocale;
