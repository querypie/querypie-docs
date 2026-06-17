import { describe, expect, it } from 'vitest';

import { filterDynamicPageMapRoutes } from './nextra-page-map';

describe('filterDynamicPageMapRoutes', () => {
  it('removes app-only dynamic routes before passing pageMap to Nextra Layout', () => {
    expect(
      filterDynamicPageMapRoutes([
        { name: 'overview', route: '/ko/overview' },
        { name: 'internal', route: '/[lang]/internal' },
        {
          name: 'nested',
          route: '/ko/nested',
          children: [
            { name: 'api', route: '/ko/nested/api' },
            { name: '[version]', route: '/[lang]/sandbox/[version]' },
          ],
        },
      ]),
    ).toEqual([
      { name: 'overview', route: '/ko/overview' },
      {
        name: 'nested',
        route: '/ko/nested',
        children: [{ name: 'api', route: '/ko/nested/api' }],
      },
    ]);
  });
});
