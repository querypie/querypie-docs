'use client';

import React from 'react';
import LanguageSelector from './language-selector';

interface MainLayoutProps {
  children: React.ReactNode;
  currentLang: string;
}

export default function MainLayoutObsoleted({ children, currentLang }: MainLayoutProps) {
  return (
    <>
      <LanguageSelector currentLang={currentLang} />
      {children}
    </>
  );
}
