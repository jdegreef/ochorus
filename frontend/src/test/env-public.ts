/**
 * Test stand-in for SvelteKit's `$env/static/public` and `$env/dynamic/public`.
 * `config.ts` (pulled in transitively via `api.ts`) reads the API base URL from
 * these; in unit tests the empty string (same-origin) is fine — no test performs
 * a real network round trip.
 */
export const PUBLIC_API_BASE_URL = '';
export const PUBLIC_SUPABASE_URL = '';
export const PUBLIC_SUPABASE_ANON_KEY = '';
export const PUBLIC_SENTRY_DSN = '';
export const env: Record<string, string | undefined> = {};
