// Import the custom layout component
import CustomTocLayout from '@/components/custom-toc-layout';

// Use only basic HTML elements for MDX components to avoid SSR issues
export const useMDXComponents = components => {
  // Filter out undefined components
  const filteredComponents = {};
  if (components) {
    Object.keys(components).forEach(key => {
      if (components[key] !== undefined) {
        filteredComponents[key] = components[key];
      }
    });
  }

  return {
    // Use standard HTML elements only
    a: 'a',
    button: 'button',
    details: 'details',
    summary: 'summary',
    div: 'div',
    span: 'span',
    p: 'p',
    h1: 'h1',
    h2: 'h2',
    h3: 'h3',
    h4: 'h4',
    h5: 'h5',
    h6: 'h6',
    ul: 'ul',
    ol: 'ol',
    li: 'li',
    img: 'img',
    code: 'code',
    pre: 'pre',
    blockquote: 'blockquote',
    table: 'table',
    thead: 'thead',
    tbody: 'tbody',
    tr: 'tr',
    th: 'th',
    td: 'td',
    strong: 'strong',
    em: 'em',
    br: 'br',
    hr: 'hr',
    section: 'section',
    article: 'article',
    header: 'header',
    footer: 'footer',
    nav: 'nav',
    aside: 'aside',
    main: 'main',
    figure: 'figure',
    figcaption: 'figcaption',
    // Add wrapper component
    wrapper: CustomTocLayout,
    ...filteredComponents,
  };
};
