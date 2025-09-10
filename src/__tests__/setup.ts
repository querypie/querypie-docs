import '@testing-library/jest-dom'
import React from 'react'

// Make React available globally
global.React = React

// Mock IntersectionObserver with a complete interface
class MockIntersectionObserver {
  root: Element | null = null
  rootMargin: string = '0px'
  thresholds: ReadonlyArray<number> = [0]
  
  constructor(
    public callback: IntersectionObserverCallback,
    public options?: IntersectionObserverInit
  ) {
    // Ensure root is Element or null, not Document
    this.root = (options?.root instanceof Element) ? options.root : null
    this.rootMargin = options?.rootMargin || '0px'
    this.thresholds = options?.threshold ? 
      (Array.isArray(options.threshold) ? options.threshold : [options.threshold]) : 
      [0]
  }
  
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
}

global.IntersectionObserver = MockIntersectionObserver as typeof IntersectionObserver

// Mock getComputedStyle
global.getComputedStyle = () => ({
  getPropertyValue: () => '0px'
} as unknown as CSSStyleDeclaration)

// Mock document.body with addEventListener
Object.defineProperty(document, 'body', {
  value: {
    style: {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {}
  },
  writable: true
})

// Mock window
Object.defineProperty(global, 'window', {
  value: {
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {}
  },
  writable: true
})
