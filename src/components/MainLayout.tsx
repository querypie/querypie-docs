'use client';

import React from 'react';
import LanguageSelector from './LanguageSelector';

interface MainLayoutProps {
  children: React.ReactNode;
  currentLang: string;
}

export default function MainLayout({ children, currentLang }: MainLayoutProps) {
  return (
    <>
      <LanguageSelector currentLang={currentLang} />
      {children}
    </>
  );
}
