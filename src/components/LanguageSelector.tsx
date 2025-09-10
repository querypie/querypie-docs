'use client';

import React from 'react';
import { addBasePath } from 'next/dist/client/add-base-path';

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

// Utility functions
export const getCurrentLanguage = (currentLang: string): LanguageOption => {
  return languages.find(lang => lang.code === currentLang) || languages[0];
};

export const getCurrentPagePath = (pathname: string, currentLang: string): string => {
  return pathname.replace(`/${currentLang}`, '') || '/';
};

// Language change handler with cookie support
export const handleLanguageChange = (lang: string, currentLang: string, pathname: string): void => {
  // Set cookie for language preference
  const date = new Date(Date.now() + ONE_YEAR);
  document.cookie = `NEXT_LOCALE=${lang}; expires=${date.toUTCString()}; path=/`;
  
  // Navigate to the new language URL
  const newPath = pathname.replace(`/${currentLang}`, `/${lang}`);
  location.href = addBasePath(newPath);
};

export const generateLanguageSelectorHTML = (currentLang: string, pathname: string): string => {
  const languageButtons = languages.map(language => {
    const isActive = language.code === currentLang;
    
    return `
      <button 
        class="language-button ${isActive ? 'active' : 'inactive'}" 
        data-lang="${language.code}"
        ${isActive ? 'disabled' : ''}
      >
        <span>${language.flag}</span>
        <span>${language.name}</span>
      </button>
    `;
  }).join('');

  return `
    <div class="language-selector-toc">
      <div class="language-selector-title">
        <span>🌐</span>
        <span>Language</span>
      </div>
      <div class="language-buttons">
        ${languageButtons}
      </div>
    </div>
  `;
};

// CSS styles as a string
export const languageSelectorStyles = `
  .language-selector-toc {
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 16px;
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

  .language-button.active:hover:not(:disabled) {
    background: #0051cc;
    color: white;
  }

  .language-button.inactive {
    background: #f8f9fa;
    color: #495057;
  }

  .language-button.inactive:hover:not(:disabled) {
    background: #e9ecef;
    color: #495057;
  }
`;

// Function to inject styles into the document
export const injectLanguageSelectorStyles = (): void => {
  if (typeof document !== 'undefined' && !document.querySelector('#language-selector-styles')) {
    const style = document.createElement('style');
    style.id = 'language-selector-styles';
    style.textContent = languageSelectorStyles;
    document.head.appendChild(style);
  }
};

// Main component for TOC integration
interface LanguageSelectorProps {
  currentLang: string;
}

export default function LanguageSelector({ currentLang }: LanguageSelectorProps) {
  React.useEffect(() => {
    // Inject styles
    injectLanguageSelectorStyles();

    // Add language selector to TOC
    const addLanguageSelector = () => {
      const tocContainer = document.querySelector('nav.nextra-toc');
      if (tocContainer && !tocContainer.querySelector('.language-selector-toc')) {
        const html = generateLanguageSelectorHTML(currentLang, window.location.pathname);
        tocContainer.insertAdjacentHTML('afterbegin', html);
        
        // Add event listeners to language buttons
        const languageButtons = tocContainer.querySelectorAll('.language-button[data-lang]');
        languageButtons.forEach(button => {
          button.addEventListener('click', (e) => {
            e.preventDefault();
            const targetLang = button.getAttribute('data-lang');
            if (targetLang && targetLang !== currentLang) {
              handleLanguageChange(targetLang, currentLang, window.location.pathname);
            }
          });
        });
      }
    };

    addLanguageSelector();
    const timeoutId = setTimeout(addLanguageSelector, 100);
    return () => clearTimeout(timeoutId);
  }, [currentLang]);

  return null; // This component doesn't render anything directly
}
