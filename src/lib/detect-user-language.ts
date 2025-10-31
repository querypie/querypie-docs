import {NextRequest} from 'next/server';
import {middlewareLogger} from './logger';

// Supported languages
export const supportedLanguages = ['en', 'ko', 'ja'];
const defaultLanguage = 'en';
const cookieName = 'NEXT_LOCALE';

/**
 * Detects language from NEXT_LOCALE cookie
 * @param request NextRequest object
 * @returns Language code if found and valid, null otherwise
 */
function detectLanguageFromCookie(request: NextRequest): string | null {
  const cookieValue = request.cookies.get(cookieName)?.value;
  
  if (!cookieValue) {
    middlewareLogger.debug('NEXT_LOCALE cookie not found');
    return null;
  }

  // Extract language code (handle cases like "ko-KR" -> "ko")
  const langCode = cookieValue.split('-')[0].toLowerCase();
  
  if (supportedLanguages.includes(langCode)) {
    middlewareLogger.debug('Language detected from NEXT_LOCALE cookie', { 
      lang: langCode,
      cookieValue 
    });
    return langCode;
  }

  middlewareLogger.debug('Invalid language in NEXT_LOCALE cookie', { 
    cookieValue,
    langCode 
  });
  return null;
}

/**
 * Detects language from Accept-Language header
 * @param request NextRequest object
 * @returns Language code if found and valid, null otherwise
 */
function detectLanguageFromAcceptHeader(request: NextRequest): string | null {
  const acceptLanguage = request.headers.get('accept-language');
  
  if (!acceptLanguage) {
    middlewareLogger.debug('Accept-Language header not found');
    return null;
  }

  // Parse Accept-Language header (e.g., "ko-KR,ko;q=0.9,en;q=0.8")
  const languages = acceptLanguage
    .split(',')
    .map(lang => {
      const [code, qValue] = lang.trim().split(';q=');
      return {
        code: code.split('-')[0].toLowerCase(), // Extract language code (ko from ko-KR)
        quality: qValue ? parseFloat(qValue) : 1.0
      };
    })
    .sort((a, b) => b.quality - a.quality);

  // Find the first supported language
  for (const lang of languages) {
    if (supportedLanguages.includes(lang.code)) {
      middlewareLogger.debug('Language detected from Accept-Language header', { 
        lang: lang.code, 
        quality: lang.quality,
        acceptLanguage 
      });
      return lang.code;
    }
  }

  middlewareLogger.debug('No supported language found in Accept-Language header', { 
    acceptLanguage 
  });
  return null;
}

/**
 * Detects user language from cookie first, then Accept-Language header
 * Falls back to default language if neither source provides a valid language
 * @param request NextRequest object
 * @returns Language code (guaranteed to be one of supportedLanguages)
 */
export function detectUserLanguage(request: NextRequest): string {
  // First, try to get language from a cookie
  const cookieLang = detectLanguageFromCookie(request);
  if (cookieLang) {
    return cookieLang;
  }

  // If the cookie is not available or invalid, try Accept-Language header
  const headerLang = detectLanguageFromAcceptHeader(request);
  if (headerLang) {
    return headerLang;
  }

  // Default fallback
  middlewareLogger.debug('Using default language', { lang: defaultLanguage });
  return defaultLanguage;
}

