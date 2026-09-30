/**
 * The paths the static host answers with the SPA shell (`200.html`, HTTP 200).
 *
 * Everything else that has no prerendered file gets `404.html` — the same app
 * shell, so a reader still sees the app's own not-found page (or, for a page
 * that exists but missed the build, the page itself) — but with an honest 404
 * STATUS. That status is the point: the old `/* -> /200.html` catch-all
 * answered 200 for every typo'd slug, retired WordPress URL and untranslated
 * `/es/books/<en-only>/`, which Google files as soft 404s and keeps
 * re-crawling instead of the real pages.
 *
 * So the 200-shell list is exactly the routes that are never prerendered
 * (`prerender = false`, client-only), plus the two account pages. Those two do
 * prerender, but to `login.html`, and Render never maps `/login` to it without
 * a rewrite, so they have always been served this shell (as under the old
 * catch-all). Pointing them at their own .html is possible but needs every
 * locale's copy to exist: a rewrite to a missing file is a blank 200.
 *
 * render.yaml repeats each of these for every UI locale; `shellRoutes.test.ts`
 * holds the two in step and walks the route tree so a new client-only route
 * can't silently answer 404.
 *
 * Patterns use Render's syntax: an exact path, or a `/*` suffix for a subtree.
 * Plain data, no imports — `scripts/serve-build.mjs` reads it too.
 */
export const SHELL_ROUTES = [
	'/admin',
	'/admin/*',
	'/settings',
	'/favorites',
	'/notebook',
	'/notebook/*',
	'/reading',
	'/login',
	'/reset-password'
] as const;

/** Whether `pathname` (locale prefix stripped) matches a SHELL_ROUTES pattern. */
export function isShellPath(pathname: string): boolean {
	const path = pathname.length > 1 ? pathname.replace(/\/$/, '') : pathname;
	return SHELL_ROUTES.some((p) =>
		p.endsWith('/*') ? path.startsWith(p.slice(0, -1)) : path === p
	);
}
