import { fireEvent, render, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import LanguageSelector2, { createLanguagePath } from './language-selector2';

const localeState = vi.hoisted(() => ({
  current: 'ko',
}));

vi.mock('@/lib/use-locale', () => ({
  default: () => localeState.current,
}));

describe('LanguageSelector2', () => {
  beforeEach(() => {
    localeState.current = 'ko';
  });

  it('renders the current language as a dropdown trigger before opening the menu', () => {
    const container = document.createElement('div');
    const result = render(<LanguageSelector2 />, {
      baseElement: container,
      container,
    });

    const trigger = within(result.container).getByRole('button', { name: /한국어/ });

    expect(trigger).toHaveAttribute('aria-haspopup', 'menu');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(within(result.container).queryByRole('menu')).not.toBeInTheDocument();
  });

  it('opens the language menu and marks the current locale', () => {
    const container = document.createElement('div');
    const result = render(<LanguageSelector2 />, {
      baseElement: container,
      container,
    });

    fireEvent.click(within(result.container).getByRole('button', { name: /한국어/ }));

    expect(within(result.container).getByRole('menu', { name: 'Language' })).toBeTruthy();
    expect(within(result.container).getByRole('menuitemradio', { name: '한국어' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
    expect(within(result.container).getByRole('menuitemradio', { name: 'English' })).toHaveAttribute(
      'aria-checked',
      'false',
    );
    expect(within(result.container).getByRole('menuitemradio', { name: '日本語' })).toHaveAttribute(
      'aria-checked',
      'false',
    );
  });

  it('closes the menu with Escape', () => {
    const container = document.createElement('div');
    const result = render(<LanguageSelector2 />, {
      baseElement: container,
      container,
    });

    fireEvent.click(within(result.container).getByRole('button', { name: /한국어/ }));
    fireEvent.keyDown(document, { key: 'Escape' });

    expect(within(result.container).queryByRole('menu')).not.toBeInTheDocument();
  });
});

describe('createLanguagePath', () => {
  it('replaces the current locale segment while preserving the rest of the path', () => {
    expect(createLanguagePath('ja', 'en', '/en/user-manual/database-access-control')).toBe(
      '/ja/user-manual/database-access-control',
    );
  });
});
