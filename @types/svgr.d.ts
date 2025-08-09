declare module '*.svg?svgr' {
  import * as React from 'react'
  const ReactComponent: React.FunctionComponent<
    React.SVGProps<SVGSVGElement> & { title?: string }
  >
  export default ReactComponent
}

// Optional: keep raw SVG imports typed as string (non-svgr case)
declare module '*.svg' {
  const content: string
  export default content
}


