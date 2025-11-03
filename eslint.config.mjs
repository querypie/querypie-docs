import pluginUnusedImports from 'eslint-plugin-unused-imports';
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import nextPlugin from '@next/eslint-plugin-next';

export default tseslint.config(
  // 무시할 파일들
  {
    ignores: [
      '**/node_modules/**',
      '**/.next/**',
      '**/dist/**',
      '**/build/**',
      '**/*.config.{js,mjs,ts}',
      '**/coverage/**',
    ],
  },
  // 기본 JavaScript 설정
  js.configs.recommended,
  // TypeScript 설정
  ...tseslint.configs.recommended,
  // src/ 디렉토리의 모든 TypeScript/JavaScript 파일
  {
    files: ['src/**/*.{js,jsx,ts,tsx}'],
    plugins: {
      '@typescript-eslint': tseslint.plugin,
      'react-hooks': reactHooks,
      '@next/next': nextPlugin,
      'unused-imports': pluginUnusedImports,
    },
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    rules: {
      // TypeScript: unused-vars는 unused-imports 플러그인이 처리하므로 비활성화
      '@typescript-eslint/no-unused-vars': 'off',
      
      // React Hooks: 필수 규칙 (Hooks 규칙 위반 방지)
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      
      // Next.js: 권장 규칙 + Core Web Vitals 규칙
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs['core-web-vitals'].rules,
      
      // Next.js: 프로젝트 특성상 비활성화하는 규칙들
      '@next/next/no-html-link-for-pages': 'off', // 외부 링크 사용 가능하도록
      '@next/next/no-img-element': 'off', // MDX에서 img 사용 허용
      
      // Unused imports: 사용하지 않는 import 자동 제거
      'unused-imports/no-unused-imports': 'error',
      'unused-imports/no-unused-vars': [
        'warn',
        {
          vars: 'all',
          varsIgnorePattern: '^_', // _로 시작하는 변수는 무시
          args: 'after-used', // 사용된 매개변수 이후의 것만 경고
          argsIgnorePattern: '^_', // _로 시작하는 매개변수는 무시
        },
      ],
    },
  },
);
