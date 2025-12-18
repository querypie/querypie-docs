'use client'

import { useEffect } from 'react'

/**
 * Component to fix table column width synchronization
 * Ensures that tbody rows use the same column widths as thead
 */
export default function TableWidthFix() {
  useEffect(() => {
    const syncTableColumnWidths = () => {
      const tables = document.querySelectorAll('main table')
      
      tables.forEach((table) => {
        const thead = table.querySelector('thead')
        const tbody = table.querySelector('tbody')
        
        if (thead && tbody) {
          const theadCells = Array.from(thead.querySelectorAll('th, td'))
          
          if (theadCells.length === 0) return
          
          // Get computed widths from thead cells
          const theadWidths = theadCells.map((cell) => {
            const computed = window.getComputedStyle(cell)
            return computed.width
          })
          
          // Apply thead column widths to all tbody rows
          const allTbodyRows = tbody.querySelectorAll('tr')
          allTbodyRows.forEach((row) => {
            const rowCells = Array.from(row.querySelectorAll('td, th'))
            rowCells.forEach((cell, cellIndex) => {
              if (theadWidths[cellIndex]) {
                ;(cell as HTMLElement).style.width = theadWidths[cellIndex]
                ;(cell as HTMLElement).style.minWidth = theadWidths[cellIndex]
                ;(cell as HTMLElement).style.maxWidth = theadWidths[cellIndex]
              }
            })
          })
        }
      })
    }
    
    // Run on mount and after a short delay to ensure DOM is ready
    syncTableColumnWidths()
    const timeoutId = setTimeout(syncTableColumnWidths, 100)
    
    // Also run when window is resized
    window.addEventListener('resize', syncTableColumnWidths)
    
    return () => {
      clearTimeout(timeoutId)
      window.removeEventListener('resize', syncTableColumnWidths)
    }
  }, [])
  
  return null // This component doesn't render anything
}

