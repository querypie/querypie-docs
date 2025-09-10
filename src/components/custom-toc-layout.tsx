import React from 'react';
import { CustomTocLayoutProps, CustomTocLayoutPropsSchema } from './schema';

// Server-safe components (no client-side interactions)
const ThemeSwitch = ({ darkMode }: { darkMode?: boolean }) => {
  if (!darkMode) return null;
  
  return (
    <div className="nx-flex nx-items-center nx-space-x-1">
      <button
        className="nx-p-2 nx-rounded-md hover:nx-bg-gray-100 dark:hover:nx-bg-gray-800"
        aria-label="Toggle theme"
      >
        <svg className="nx-w-5 nx-h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      </button>
    </div>
  );
};


const BackToTop = ({ toc }: { toc?: { backToTop?: React.ReactNode } }) => {
  if (!toc?.backToTop) return null;
  
  return (
    <button
      className="nx-fixed nx-bottom-4 nx-right-16 nx-p-2 nx-bg-blue-600 nx-text-white nx-rounded-full nx-shadow-lg hover:nx-bg-blue-700 nx-transition-colors"
      aria-label="Back to top"
    >
      <svg className="nx-w-5 nx-h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
    </button>
  );
};

export default function CustomTocLayout(props: CustomTocLayoutProps) {
  // Validate props using schema
  const validatedProps = CustomTocLayoutPropsSchema.parse(props);
  
  const {
    children,
    banner,
    navbar,
    footer,
    editLink,
    docsRepositoryBase,
    feedback,
    sidebar,
    search,
    toc,
    darkMode,
    themeSwitch,
    i18n,
    lastUpdated,
    pageMap,
    navigation,
    nextThemes,
    ...rest
  } = validatedProps;

  // Server-side rendering fallback
  const sidebarOpen = sidebar?.defaultOpen ?? true;

  // Generate feedback URL dynamically like nextra-theme-docs
  const getFeedbackUrl = () => {
    if (feedback?.link) {
      return feedback.link;
    }
    
    // Use docsRepositoryBase to construct the feedback URL
    const baseUrl = docsRepositoryBase || 'https://github.com/shuding/nextra';
    const pageTitle = typeof window !== 'undefined' ? document.title : 'Page';
    const encodedTitle = encodeURIComponent(`Feedback for "${pageTitle}"`);
    
    return `${baseUrl}/issues/new?title=${encodedTitle}&labels=${feedback?.labels || 'feedback'}`;
  };

  return (
    <div className="nx-bg-white dark:nx-bg-dark nx-text-gray-900 dark:nx-text-gray-100 nx-min-h-screen">
      {/* Banner */}
      {banner && (
        <div className="nx-border-b nx-border-gray-200 dark:nx-border-gray-800">
          {banner}
        </div>
      )}

      {/* Navbar */}
      {navbar && (
        <div className="nx-sticky nx-top-0 nx-z-50 nx-w-full nx-border-b nx-border-gray-200 dark:nx-border-gray-800 nx-bg-white/80 dark:nx-bg-dark/80 nx-backdrop-blur-sm">
          {navbar}
        </div>
      )}

      <div className="nx-flex nx-min-h-screen">
        {/* Sidebar */}
        <aside className={`
          nx-fixed nx-inset-y-0 nx-left-0 nx-z-40 nx-w-64 nx-bg-white dark:nx-bg-dark nx-border-r nx-border-gray-200 dark:nx-border-gray-800 nx-transform nx-transition-transform nx-duration-300 nx-ease-in-out
          lg:nx-translate-x-0 lg:nx-static lg:nx-inset-0
          ${sidebarOpen ? 'nx-translate-x-0' : '-nx-translate-x-full'}
        `}>
          <div className="nx-flex nx-flex-col nx-h-full">
            <div className="nx-flex-1 nx-overflow-y-auto nx-py-4">
              <nav className="nx-px-4 nx-space-y-2">
                {/* TOC */}
                {toc && (
                  <div className="nx-mb-6">
                    <div className="nx-text-sm nx-font-medium nx-text-gray-900 dark:nx-text-gray-100 nx-mb-3">
                      {toc.title}
                    </div>
                    <div className="nx-space-y-1">
                      {/* TOC items would be rendered here */}
                      <div className="nx-text-sm nx-text-gray-500 dark:nx-text-gray-400">
                        Table of Contents
                      </div>
                    </div>
                    {toc.extraContent && (
                      <div className="nx-mt-4">
                        {toc.extraContent}
                      </div>
                    )}
                  </div>
                )}

                {/* Navigation items */}
                <div className="nx-space-y-1">
                  <div className="nx-text-sm nx-text-gray-500 dark:nx-text-gray-400">
                    Navigation
                  </div>
                  {/* Navigation items would be rendered here based on pageMap */}
                </div>
              </nav>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="nx-flex-1 nx-min-w-0">
          <div className="nx-px-4 nx-py-6 lg:nx-px-8">
            {children}
            
            {/* Last updated */}
            {lastUpdated && (
              <div className="nx-mt-8 nx-pt-4 nx-border-t nx-border-gray-200 dark:nx-border-gray-800">
                {lastUpdated}
              </div>
            )}

            {/* Navigation (prev/next) */}
            {navigation && (
              <div className="nx-mt-8 nx-pt-4 nx-border-t nx-border-gray-200 dark:nx-border-gray-800 nx-flex nx-justify-between">
                <div>
                  {typeof navigation === 'object' && navigation.prev && (
                    <button className="nx-text-blue-600 dark:nx-text-blue-400 hover:nx-underline">
                      ← Previous
                    </button>
                  )}
                </div>
                <div>
                  {typeof navigation === 'object' && navigation.next && (
                    <button className="nx-text-blue-600 dark:nx-text-blue-400 hover:nx-underline">
                      Next →
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Footer */}
      {footer && (
        <footer className="nx-border-t nx-border-gray-200 dark:nx-border-gray-800 nx-bg-gray-50 dark:nx-bg-dark">
          <div className="nx-px-4 nx-py-6 lg:nx-px-8">
            {footer}
          </div>
        </footer>
      )}

      {/* Edit link */}
      {editLink && (
        <div className="nx-fixed nx-bottom-4 nx-right-4">
          <a
            href={typeof editLink === 'string' ? editLink : '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="nx-inline-flex nx-items-center nx-px-3 nx-py-2 nx-text-sm nx-font-medium nx-text-gray-700 nx-bg-white nx-border nx-border-gray-300 nx-rounded-md nx-shadow-sm hover:nx-bg-gray-50 dark:nx-bg-gray-800 dark:nx-text-gray-300 dark:nx-border-gray-600 dark:hover:nx-bg-gray-700"
          >
            <svg className="nx-w-4 nx-h-4 nx-mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Edit this page
          </a>
        </div>
      )}

      {/* Feedback */}
      {feedback && (
        <div className="nx-fixed nx-bottom-4 nx-left-4">
          <a
            href={getFeedbackUrl()}
            target="_blank"
            rel="noopener noreferrer"
            className="nx-inline-flex nx-items-center nx-px-3 nx-py-2 nx-text-sm nx-font-medium nx-text-gray-700 nx-bg-white nx-border nx-border-gray-300 nx-rounded-md nx-shadow-sm hover:nx-bg-gray-50 dark:nx-bg-gray-800 dark:nx-text-gray-300 dark:nx-border-gray-600 dark:hover:nx-bg-gray-700"
          >
            <svg className="nx-w-4 nx-h-4 nx-mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            {feedback.content}
          </a>
        </div>
      )}

      {/* Back to top */}
      <BackToTop toc={toc} />
    </div>
  );
}