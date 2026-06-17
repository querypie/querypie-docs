import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const layoutSource = readFileSync(join(process.cwd(), 'src/app/[lang]/layout.tsx'), 'utf8');

describe('/[lang] root layout', () => {
  it('keeps Spotlight out of the global Nextra layout', () => {
    expect(layoutSource).not.toContain('DocsSpotlightSidebar');
    expect(layoutSource).toContain('extraContent: <ConfluenceSourceLink/>');
  });
});
