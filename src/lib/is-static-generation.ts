/**
 * Check if the code is running during static generation (build time).
 * 
 * This function uses the NEXT_PHASE environment variable to determine
 * if we're in static generation phase.
 * 
 * @returns boolean True if running during static generation, false otherwise
 */
export function isStaticGeneration(): boolean {
  // If running in browser, it's not static generation
  if (typeof window !== 'undefined') {
    return false;
  }

  // NEXT_PHASE is set during Next.js build process
  // 'phase-production-build' indicates static export/generation phase
  return process.env.NEXT_PHASE === 'phase-production-build';
}
