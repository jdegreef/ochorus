import { browser } from '$app/environment';
import { env } from '$env/dynamic/public';
import type { SupabaseClient } from '@supabase/supabase-js';

/**
 * Supabase browser client, loaded and created lazily, and only when both env
 * vars are set. Auth is entirely optional: with no Supabase project configured
 * the client is null and the app runs anonymously (login UI hides itself). This
 * mirrors the backend, which validates Supabase JWTs but serves the library to
 * AllowAny.
 *
 * The import is dynamic, which is the point. `createClient` was imported at the
 * top of this module, and this module is reached from the root layout — so
 * `@supabase/supabase-js` (auth, postgrest, realtime and storage clients) sat in
 * the entry chunk of every prerendered SEO page, downloaded by every anonymous
 * reader who will never sign in. It was created lazily and loaded eagerly; only
 * the second half is now true as well.
 *
 * `import type` above is erased at compile time, so the type costs nothing.
 */

const url = env.PUBLIC_SUPABASE_URL;
const anonKey = env.PUBLIC_SUPABASE_ANON_KEY;

/** Synchronous, because callers use it to decide whether to render login UI. */
export const authEnabled = Boolean(browser && url && anonKey);

let client: SupabaseClient | null = null;
/** The in-flight load, so concurrent callers share one import and one client. */
let loading: Promise<SupabaseClient | null> | null = null;

export function supabase(): Promise<SupabaseClient | null> {
	if (!authEnabled) return Promise.resolve(null);
	if (client) return Promise.resolve(client);
	if (!loading) {
		loading = import('@supabase/supabase-js').then(({ createClient }) => {
			client = createClient(url!, anonKey!, {
				// detectSessionInUrl lets the client complete the Google OAuth and
				// magic-link redirects automatically when the user lands back on the
				// app, so no dedicated /auth/callback route is needed.
				auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
			});
			return client;
		});
	}
	return loading;
}
