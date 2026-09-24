/**
 * Content-Security-Policy directives — the SINGLE source of the app's CSP.
 *
 * Consumed by `svelte.config.js` (`kit.csp`, hash mode), which injects the
 * policy as a <meta http-equiv> on every prerendered page and the 200.html
 * fallback. `src/lib/csp.test.ts` imports this same object to assert it against
 * the code. Kept as its own plain-data module (no side effects) so the test can
 * import it without executing svelte.config.js.
 *
 * The CSP used to be a static header in render.yaml. It moved here because a
 * static header cannot carry the hash of SvelteKit's per-build inline bootstrap
 * (its hash changes every build), which forced `script-src 'unsafe-inline'` and
 * left the localStorage Supabase token protected by `connect-src` alone. In hash
 * mode SvelteKit computes that hash at build time, so `script-src` drops
 * `'unsafe-inline'`: an injected inline <script> or event handler no longer
 * matches a hash and is refused. render.yaml keeps the non-CSP headers; framing
 * stays covered by its `X-Frame-Options: DENY` (a <meta> CSP cannot enforce
 * `frame-ancestors`, kept below only as documentation).
 *
 * Sources use SvelteKit's convention: keyword sources WITHOUT the CSP quotes
 * (`self`, not `'self'`); hosts, schemes and hashes verbatim.
 *
 * ⚠️ connect-src is the control that stops an injected script POSTing the token
 * off-origin — every host the app dials is enumerated, and csp.test.ts fails the
 * build if code starts fetching a host this list does not cover.
 * ⚠️ The Supabase host is pinned to the exact project, NOT `*.supabase.co`:
 * anyone can create a free `<ref>.supabase.co`, so a wildcard would let an
 * injected script exfiltrate the token to an attacker's project. Update the ref
 * if PUBLIC_SUPABASE_URL changes, or login breaks with a CSP violation.
 * ⚠️ Plausible is in both script-src (loads /js/script.js) and connect-src (the
 * script POSTs to /api/event); it stays even when analytics is unset (the script
 * simply never loads). Self-hosting = swap the host in both.
 */
export const cspDirectives = {
	'default-src': ['self'],
	'script-src': [
		'self',
		'https://plausible.io',
		// The static app.html theme-boot script. SvelteKit hashes the inline
		// scripts IT emits (the per-build bootstrap) but NOT a template script, so
		// its hash is pinned here by hand. Stable (the boot script text is
		// build-invariant) and guarded by csp.test.ts, which fails the build if
		// app.html changes and this is not updated — rather than silently blocking
		// the theme boot in production.
		'sha256-DtEq9iS9eaAu4vsACfAB1Cm79UkCl9ze+bvjSv19/U0=',
		// SvelteKit injects onload/onerror="this.__e=event" inline event handlers
		// to replay pre-hydration load/error events. CSP hashes don't cover
		// event-handler ATTRIBUTES — 'unsafe-hashes' does — and this admits exactly
		// `this.__e=event`: an injected onerror="fetch(evil)" has a different hash
		// and is still refused.
		'unsafe-hashes',
		'sha256-7dQwUgLau1NFCCGjfn9FsYptB6ZtWxJin6VohGIu20I='
	],
	'style-src': ['self', 'unsafe-inline'],
	// Every image the app paints is same-origin: book covers under `/covers/`
	// and author portraits under `/portraits/` are repo-committed static assets
	// served by the site itself, never hot-linked. `data:` covers the inlined
	// favicon/placeholder rasters; `blob:` the covers the offline download
	// reconstructs from the cache. NO blanket `https:` — it let an XSS-injected
	// `<img>` beacon to any host on the internet, and nothing the reader sees
	// needs it. The one path that used to lean on it (an admin pasting an
	// external cover URL at import) was removed: covers are repo assets, so
	// import no longer stores a cover_url at all.
	'img-src': ['self', 'data:', 'blob:'],
	// `data:` because Vite inlines small font subsets as data:font/woff2 URIs
	// under its assetsInlineLimit; without it the face is blocked at runtime.
	'font-src': ['self', 'data:'],
	'connect-src': [
		'self',
		'https://ochorus-api.onrender.com',
		'https://api.ochorus.com',
		'https://eywunobxqijvwymdzlwy.supabase.co',
		'https://api.dictionaryapi.dev',
		'https://*.ingest.sentry.io',
		'https://*.ingest.us.sentry.io',
		'https://plausible.io'
	],
	'manifest-src': ['self'],
	'worker-src': ['self'],
	'media-src': ['self'],
	'object-src': ['none'],
	'frame-src': ['none'],
	'frame-ancestors': ['none'],
	'base-uri': ['self'],
	'form-action': ['self']
};
