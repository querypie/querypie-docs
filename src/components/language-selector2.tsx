'use client';

import React from 'react';
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

// Language change handler with cookie support
export const handleLanguageChange = (lang: string, currentLang: string, pathname: string): void => {
  // Set cookie for language preference
  const date = new Date(Date.now() + ONE_YEAR);
  document.cookie = `NEXT_LOCALE=${lang}; expires=${date.toUTCString()}; path=/`;
  
  // Navigate to the new language URL
  const newPath = pathname.replace(`/${currentLang}`, `/${lang}`);
  location.href = addBasePath(newPath);
};

// CSS styles as a string
export const languageSelectorStyles = `
  .language-selector-toc {
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 16px;
  }

  .dark .language-selector-toc {
    border-bottom-color: #374151;
  }

  .language-selector-title {
    font-size: 14px;
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

  .globe-icon {
    color: #6b7280;
  }

  .dark .globe-icon {
    color: #9ca3af;
  }

  .language-buttons {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .language-button {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    text-decoration: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s ease;
    width: 100%;
    box-sizing: border-box;
    border: none;
    cursor: pointer;
    background: none;
  }

  .language-button:disabled {
    cursor: default;
  }

  .language-button:hover:not(:disabled) {
    transform: translateY(-1px);
    text-decoration: none;
  }

  .language-button.active {
    background: #0070f3;
    color: white;
  }

  .dark .language-button.active {
    background: #3b82f6;
  }

  .language-button.active:hover:not(:disabled) {
    background: #0051cc;
    color: white;
  }

  .dark .language-button.active:hover:not(:disabled) {
    background: #2563eb;
  }

  .language-button.inactive {
    background: #f8f9fa;
    color: #495057;
  }

  .dark .language-button.inactive {
    background: #374151;
    color: #d1d5db;
  }

  .language-button.inactive:hover:not(:disabled) {
    background: #e9ecef;
    color: #495057;
  }

  .dark .language-button.inactive:hover:not(:disabled) {
    background: #4b5563;
    color: #f3f4f6;
  }
`;

// Main component
export default function LanguageSelector2() {
  const currentLang = useLocale('en');
  const handleClick = (lang: string, e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    if (lang !== currentLang) {
      handleLanguageChange(lang, currentLang, window.location.pathname);
    }
  };

  return (
    <>
      <style>{languageSelectorStyles}</style>
      <div className="language-selector-toc">
        <div className="language-selector-title">
          <span>🌐</span>
          <span>Language</span>
        </div>
        <div className="language-buttons">
          {languages.map((language) => {
            const isActive = language.code === currentLang;
            return (
              <button
                key={language.code}
                className={`language-button ${isActive ? 'active' : 'inactive'}`}
                disabled={isActive}
                onClick={(e) => handleClick(language.code, e)}
              >
                <span>{language.flag}</span>
                <span>{language.name}</span>
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}

