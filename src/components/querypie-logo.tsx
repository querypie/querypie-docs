import React from 'react';

/**
 * QueryPieLogo HTML structure as string
 * Used for DOM manipulation scenarios (e.g., Redoc logo replacement)
 */
export const QUERYPIE_LOGO_HTML = `
  <div style="display: flex; align-items: center; gap: 7px;">
    <img src="/icon-32.png" alt="QueryPie Logo" width="18" height="18" />
    <div>
      <b>QueryPie</b> <span style="opacity: 60%;">ACP</span>
    </div>
  </div>
`;

/**
 * QueryPieLogo Component
 *
 * Reusable logo component for QueryPie ACP.
 * Displays the QueryPie logo with icon and text.
 *
 * @example
 * ```tsx
 * <QueryPieLogo />
 * ```
 */
export function QueryPieLogo() {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
        <img src="/icon-32.png" alt="QueryPie Logo" width={18} height={18} />
        <div>
          <b>QueryPie</b> <span style={{ opacity: '60%' }}>ACP</span>
        </div>
      </div>
    </div>
  );
}

