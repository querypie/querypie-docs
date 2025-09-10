import { describe, it, expect } from 'vitest'
import { CustomTocLayoutPropsSchema } from '../schemas'
import { z } from 'zod'
import React from 'react'

describe('CustomTocLayoutPropsSchema', () => {
  describe('기본값 검증', () => {
    it('최소한의 필수 props로 스키마가 유효해야 함', () => {
      const minimalProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: []
      }

      const result = CustomTocLayoutPropsSchema.safeParse(minimalProps)
      expect(result.success).toBe(true)
    })

    it('모든 기본값이 올바르게 설정되어야 함', () => {
      const props = {
        children: React.createElement('div', null, 'Test'),
        pageMap: []
      }

      const result = CustomTocLayoutPropsSchema.parse(props)
      
      // 기본값 검증
      expect(result.darkMode).toBe(true)
      expect(result.docsRepositoryBase).toBe('https://github.com/shuding/nextra')
      expect(result.editLink).toBe('Edit this page')
      expect(result.feedback.content).toBe('Question? Give us feedback')
      expect(result.feedback.labels).toBe('feedback')
      expect(result.i18n).toEqual([])
      expect(result.navigation).toEqual({ next: true, prev: true })
      expect(result.sidebar.defaultMenuCollapseLevel).toBe(2)
      expect(result.sidebar.defaultOpen).toBe(true)
      expect(result.sidebar.toggleButton).toBe(true)
      expect(result.themeSwitch.dark).toBe('Dark')
      expect(result.themeSwitch.light).toBe('Light')
      expect(result.themeSwitch.system).toBe('System')
      expect(result.toc.backToTop).toBe('Scroll to top')
      expect(result.toc.float).toBe(true)
      expect(result.toc.title).toBe('On This Page')
    })
  })

  describe('docsRepositoryBase 검증', () => {
    it('https로 시작하는 URL이어야 함', () => {
      const validProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        docsRepositoryBase: 'https://github.com/valid/repo'
      }

      const result = CustomTocLayoutPropsSchema.safeParse(validProps)
      expect(result.success).toBe(true)
    })

    it('http로 시작하는 URL은 유효하지 않아야 함', () => {
      const invalidProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        docsRepositoryBase: 'http://github.com/invalid/repo'
      }

      const result = CustomTocLayoutPropsSchema.safeParse(invalidProps)
      expect(result.success).toBe(false)
    })
  })

  describe('sidebar 검증', () => {
    it('defaultMenuCollapseLevel이 1 이상이어야 함', () => {
      const validProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        sidebar: { defaultMenuCollapseLevel: 1 }
      }

      const result = CustomTocLayoutPropsSchema.safeParse(validProps)
      expect(result.success).toBe(true)
    })

    it('defaultMenuCollapseLevel이 0이면 유효하지 않아야 함', () => {
      const invalidProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        sidebar: { defaultMenuCollapseLevel: 0 }
      }

      const result = CustomTocLayoutPropsSchema.safeParse(invalidProps)
      expect(result.success).toBe(false)
    })
  })

  describe('i18n 검증', () => {
    it('올바른 i18n 배열이어야 함', () => {
      const validProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        i18n: [
          { locale: 'en', name: 'English' },
          { locale: 'ko', name: '한국어' }
        ]
      }

      const result = CustomTocLayoutPropsSchema.safeParse(validProps)
      expect(result.success).toBe(true)
    })

    it('잘못된 i18n 구조는 유효하지 않아야 함', () => {
      const invalidProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        i18n: [
          { locale: 'en' }, // name이 누락
          { name: '한국어' } // locale이 누락
        ]
      }

      const result = CustomTocLayoutPropsSchema.safeParse(invalidProps)
      expect(result.success).toBe(false)
    })
  })

  describe('navigation 검증', () => {
    it('boolean 값이 올바르게 변환되어야 함', () => {
      const props = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        navigation: true
      }

      const result = CustomTocLayoutPropsSchema.parse(props)
      expect(result.navigation).toEqual({ next: true, prev: true })
    })

    it('객체 값이 그대로 유지되어야 함', () => {
      const props = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        navigation: { next: true, prev: false }
      }

      const result = CustomTocLayoutPropsSchema.parse(props)
      expect(result.navigation).toEqual({ next: true, prev: false })
    })
  })

  describe('nextThemes 검증', () => {
    it('올바른 nextThemes 설정이어야 함', () => {
      const validProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        nextThemes: {
          attribute: 'class',
          defaultTheme: 'system',
          disableTransitionOnChange: true,
          storageKey: 'theme'
        }
      }

      const result = CustomTocLayoutPropsSchema.safeParse(validProps)
      expect(result.success).toBe(true)
    })

    it('잘못된 attribute는 유효하지 않아야 함', () => {
      const invalidProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: [],
        nextThemes: {
          attribute: 'invalid-attribute'
        }
      }

      const result = CustomTocLayoutPropsSchema.safeParse(invalidProps)
      expect(result.success).toBe(false)
    })
  })

  describe('필수 필드 검증', () => {
    it('children이 없어도 유효해야 함 (선택적 필드)', () => {
      const props = {
        pageMap: []
      }

      const result = CustomTocLayoutPropsSchema.safeParse(props)
      expect(result.success).toBe(true)
    })

    it('pageMap이 없으면 유효하지 않아야 함', () => {
      const invalidProps = {
        children: React.createElement('div', null, 'Test')
      }

      const result = CustomTocLayoutPropsSchema.safeParse(invalidProps)
      expect(result.success).toBe(false)
    })
  })

  describe('타입 추론 검증', () => {
    it('스키마에서 타입을 올바르게 추론해야 함', () => {
      type CustomTocLayoutProps = z.infer<typeof CustomTocLayoutPropsSchema>
      
      // 최소한의 필수 props로 타입 검증
      const props: Partial<CustomTocLayoutProps> = {
        children: React.createElement('div', null, 'Test'),
        pageMap: []
      }

      expect(props).toBeDefined()
      expect(props.children).toBeDefined()
      expect(props.pageMap).toBeDefined()
    })

    it('완전한 props로 타입을 올바르게 추론해야 함', () => {
      type CustomTocLayoutProps = z.infer<typeof CustomTocLayoutPropsSchema>
      
      // 스키마를 통해 완전한 props 생성
      const minimalProps = {
        children: React.createElement('div', null, 'Test'),
        pageMap: []
      }
      
      const fullProps: CustomTocLayoutProps = CustomTocLayoutPropsSchema.parse(minimalProps)

      expect(fullProps).toBeDefined()
      expect(fullProps.children).toBeDefined()
      expect(fullProps.pageMap).toBeDefined()
      expect(fullProps.darkMode).toBe(true) // 기본값 확인
      expect(fullProps.docsRepositoryBase).toBe('https://github.com/shuding/nextra') // 기본값 확인
    })
  })
})
