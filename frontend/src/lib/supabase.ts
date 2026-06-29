import { browser } from '$app/environment';
import { env } from '$env/dynamic/public';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

/**
 * Supabase browser client, created lazily and only when both env vars are set.
 * Auth is entirely optional: with no Supabase project configured the client is
 * null and the app runs anonymously (login UI hides itself). This mirrors the
 * backend, which validates Supabase JWTs but serves the library to AllowAny.
 */

const url = env.PUBLIC_SUPABASE_URL;
const anonKey = env.PUBLIC_SUPABASE_ANON_KEY;

export const authEnabled = Boolean(browser && url && anonKey);

let client: SupabaseClient | null = null;

export function supabase(): SupabaseClient | null {
	if (!authEnabled) return null;
	if (!client) {
		client = createClient(url!, anonKey!, {
			auth: { persistSession: true, autoRefreshToken: true }
		});
	}
	return client;
}
