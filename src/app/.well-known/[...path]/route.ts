import { NextRequest, NextResponse } from 'next/server';

/**
 * Route handler for .well-known paths
 * 
 * This handler prevents .well-known paths from being matched to [lang] route.
 * Returns 404 for all .well-known requests to avoid routing errors.
 */
export async function GET(
  _request: NextRequest,
  _params: { params: Promise<{ path: string[] }> }
) {
  return new NextResponse('Not Found', { status: 404 });
}
