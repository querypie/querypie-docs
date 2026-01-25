import { useMDXComponents as getDocsMDXComponents } from 'nextra-theme-docs';
import Badge from '@/components/badge';

const docsComponents = getDocsMDXComponents();

export const useMDXComponents = components => ({
  ...docsComponents,
  Badge,
  ...components,
});
