import React from 'react';
import { CustomTocLayoutPropsSchema } from './schemas';
import { Layout } from 'nextra-theme-docs';

// CustomTocLayout is a wrapper around nextra-theme-docs Layout
// This allows for easy customization while maintaining full compatibility
// with nextra-theme-docs functionality

export default function CustomTocLayout(props: any) {
  // Pre-process props to ensure all required properties are present
  const processedProps = {
    ...props,
    sidebar: {
      defaultMenuCollapseLevel: 2,
      defaultOpen: true,
      toggleButton: true,
      ...props.sidebar
    },
    toc: {
      title: 'On This Page',
      backToTop: 'Scroll to top',
      float: true,
      ...props.toc
    }
  };

  // Validate props using schema
  const validatedProps = CustomTocLayoutPropsSchema.parse(processedProps);
  
  const {
    children,
    banner,
    navbar,
    footer,
    editLink,
    docsRepositoryBase,
    feedback,
    sidebar,
    search,
    toc,
    darkMode,
    themeSwitch,
    i18n,
    lastUpdated,
    pageMap,
    navigation,
    nextThemes,
    ...rest
  } = validatedProps;

  // Use validated props directly since they now have all required properties
  const layoutProps = {
    ...rest,
    banner,
    navbar,
    footer,
    editLink,
    docsRepositoryBase,
    feedback,
    sidebar,
    search,
    toc,
    darkMode,
    themeSwitch,
    i18n,
    lastUpdated,
    pageMap,
    navigation,
    nextThemes
  };

  // Use nextra-theme-docs Layout with all required props
  return (
    <Layout {...layoutProps}>
      {children}
    </Layout>
  );
}