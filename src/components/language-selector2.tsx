'use client';

import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import { CheckIcon, ChevronDownIcon, LanguageIcon } from '@heroicons/react/24/outline';
import { addBasePath } from 'next/dist/client/add-base-path';
import useLocale from '@/lib/use-locale';

// Language data and types
export interface LanguageOption {
  code: string;
  name: string;
  flag: string;
}

export const languages: LanguageOption[] = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'ja', name: '日本語', flag: '🇯🇵' },
  { code: 'ko', name: '한국어', flag: '🇰🇷' },
];

// Constants
const ONE_YEAR = 365 * 24 * 60 * 60 * 1000;

export const createLanguagePath = (lang: string, currentLang: string, pathname: string): string => {
  return pathname.replace(`/${currentLang}`, `/${lang}`);
};

// Language change handler with cookie support
export const handleLanguageChange = (lang: string, currentLang: string, pathname: string): void => {
  // Set cookie for language preference
  const date = new Date(Date.now() + ONE_YEAR);
  document.cookie = `NEXT_LOCALE=${lang}; expires=${date.toUTCString()}; path=/`;

  // Navigate to the new language URL
  const newPath = createLanguagePath(lang, currentLang, pathname);
  location.href = addBasePath(newPath);
};

// CSS styles as a string
export const languageSelectorStyles = `
  .language-selector-toc {
    padding: 0px 0px 16px 0px;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 16px;
    position: relative;
  }

  .dark .language-selector-toc {
    border-bottom-color: #374151;
  }

  .language-selector-title {
    font-size: 16px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .dark .language-selector-title {
    color: #d1d5db;
  }

  .language-selector-trigger {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: min(100%, 11rem);
    min-height: 38px;
    padding: 8px 10px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: #fff;
    color: #111827;
    font-size: 14px;
    font-weight: 500;
    box-sizing: border-box;
    cursor: pointer;
    transition: border-color 0.15s ease, background-color 0.15s ease;
  }

  .dark .language-selector-trigger {
    background: #111827;
    border-color: #4b5563;
    color: #f9fafb;
  }

  .language-selector-trigger:hover,
  .language-selector-trigger[aria-expanded="true"] {
    border-color: #6b7280;
    background: #f9fafb;
  }

  .dark .language-selector-trigger:hover,
  .dark .language-selector-trigger[aria-expanded="true"] {
    border-color: #9ca3af;
    background: #1f2937;
  }

  .language-selector-trigger-main,
  .language-option-main {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 8px;
  }

  .language-selector-icon,
  .language-selector-chevron,
  .language-option-check {
    flex: 0 0 auto;
    width: 16px;
    height: 16px;
    color: #6b7280;
  }

  .dark .language-selector-icon,
  .dark .language-selector-chevron,
  .dark .language-option-check {
    color: #9ca3af;
  }

  .language-selector-chevron {
    transition: transform 0.15s ease;
  }

  .language-selector-trigger[aria-expanded="true"] .language-selector-chevron {
    transform: rotate(180deg);
  }

  .language-selector-current,
  .language-option-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .language-selector-menu {
    position: absolute;
    z-index: 30;
    top: calc(100% - 10px);
    left: 0;
    display: flex;
    flex-direction: column;
    width: min(100%, 11rem);
    padding: 4px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: #fff;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14);
  }

  .dark .language-selector-menu {
    border-color: #4b5563;
    background: #111827;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.4);
  }

  .language-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    min-height: 34px;
    padding: 7px 8px;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: #374151;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    text-align: left;
  }

  .dark .language-option {
    color: #d1d5db;
  }

  .language-option:hover,
  .language-option:focus-visible {
    background: #f3f4f6;
    outline: none;
  }

  .dark .language-option:hover,
  .dark .language-option:focus-visible {
    background: #1f2937;
  }

  .language-option[aria-checked="true"] {
    color: #111827;
  }

  .dark .language-option[aria-checked="true"] {
    color: #f9fafb;
  }
`;

// Main component
export default function LanguageSelector2() {
  const [isOpen, setIsOpen] = useState(false);
  const menuId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const currentLang = useLocale('en');
  const currentLanguage = useMemo(
    () => languages.find(language => language.code === currentLang) ?? languages[0],
    [currentLang],
  );

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  const handleSelect = (lang: string) => {
    setIsOpen(false);

    if (lang !== currentLang) {
      handleLanguageChange(lang, currentLang, window.location.pathname);
    }
  };

  return (
    <>
      <style>{languageSelectorStyles}</style>
      <div className="language-selector-toc" ref={rootRef}>
        <div className="language-selector-title">
          <LanguageIcon aria-hidden="true" className="language-selector-icon" />
          <span>Language</span>
        </div>
        <button
          type="button"
          className="language-selector-trigger"
          aria-controls={isOpen ? menuId : undefined}
          aria-expanded={isOpen}
          aria-haspopup="menu"
          onClick={() => setIsOpen(open => !open)}
          onKeyDown={event => {
            if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              setIsOpen(true);
            }
          }}
        >
          <span className="language-selector-trigger-main">
            <span aria-hidden="true">{currentLanguage.flag}</span>
            <span className="language-selector-current">{currentLanguage.name}</span>
          </span>
          <ChevronDownIcon aria-hidden="true" className="language-selector-chevron" />
        </button>
        {isOpen && (
          <div className="language-selector-menu" id={menuId} role="menu" aria-label="Language">
            {languages.map(language => {
              const isActive = language.code === currentLang;
              return (
                <button
                  key={language.code}
                  type="button"
                  className="language-option"
                  role="menuitemradio"
                  aria-checked={isActive}
                  onClick={() => handleSelect(language.code)}
                >
                  <span className="language-option-main">
                    <span aria-hidden="true">{language.flag}</span>
                    <span className="language-option-name">{language.name}</span>
                  </span>
                  {isActive && <CheckIcon aria-hidden="true" className="language-option-check" />}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
