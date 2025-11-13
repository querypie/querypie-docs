export async function getBaseUrl(): Promise<string> {
  if (typeof window !== 'undefined') {
    throw new Error('getBaseUrl can only be used in server components');
  }

  // Use dynamic import to conditionally load next/headers
  const { headers } = await import('next/headers');
  const headersList = await headers();
  const host = headersList.get('host');
  const protocol = headersList.get('x-forwarded-proto') || 'https';
  return `${protocol}://${host}`;
}
