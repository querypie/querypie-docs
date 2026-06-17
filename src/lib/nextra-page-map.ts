import type { PageMapItem } from 'nextra';

function hasRoute(item: PageMapItem): item is PageMapItem & { route: string } {
  return 'route' in item && typeof item.route === 'string';
}

function hasChildren(item: PageMapItem): item is PageMapItem & { children: PageMapItem[] } {
  return 'children' in item && Array.isArray(item.children);
}

function hasDynamicRouteSegment(item: PageMapItem) {
  return hasRoute(item) && item.route.includes('[');
}

export function filterDynamicPageMapRoutes(pageMap: readonly PageMapItem[]): PageMapItem[] {
  return pageMap
    .filter(item => !hasDynamicRouteSegment(item))
    .map(item => {
      if (!hasChildren(item)) {
        return item;
      }

      return {
        ...item,
        children: filterDynamicPageMapRoutes(item.children),
      };
    });
}
