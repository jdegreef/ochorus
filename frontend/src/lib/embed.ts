import type { ThemePref } from '$lib/theme.svelte';

/**
 * The church-website widget: "Today from Ochorus" — the day's verse, reading
 * and sermon in a small card a church puts on its own site.
 *
 * Three pieces, which this module keeps in step:
 *
 * - `static/embed.js`, the one-line `<script>` a church pastes. It inserts a
 *   sized, lazy iframe of the page below in the language (`data-lang`) and
 *   look (`data-theme`) the tag asks for, and grows it to the height the
 *   page reports (`EMBED_HEIGHT_MESSAGE`).
 * - `/embed/today` (routes/embed), the page in that iframe. Client-only, like
 *   /today, because "today" is the reader's local date; noindex; drawn with
 *   no site chrome (the root layout asks `isEmbedRoute`); every link opens
 *   ochorus.com in a new tab, so the church's page stays where it was.
 * - render.yaml, which lets ONLY `[/<lang>]/embed/*` be framed (a
 *   `frame-ancestors` header per locale; every other path is
 *   `X-Frame-Options: DENY`) and rewrites it to the SPA shell.
 *
 * The snippet itself is shown to church leaders on the /for/ pages.
 */

/** Route ids drawn as a bare widget: no nav, footer, tab bar or prompts. */
export const isEmbedRoute = (routeId: string | null | undefined): boolean =>
	!!routeId?.startsWith('/embed/');

/** What the iframe's `?theme=` asks for, as a theme preference: `dark`,
 *  `sepia`, `auto` (the visitor's OS setting) or, by default, `light`. */
export function embedTheme(param: string | null): ThemePref {
	if (param === 'dark' || param === 'sepia') return param;
	if (param === 'auto' || param === 'system') return 'system';
	return 'light';
}

/** The `postMessage` type the widget page reports its height under; embed.js
 *  listens for the same string. */
export const EMBED_HEIGHT_MESSAGE = 'ochorus:embed-height';

/** The tag a church pastes, for a widget in `lang`. */
export const embedSnippet = (siteUrl: string, lang: string): string =>
	`<script src="${siteUrl}/embed.js" data-widget="today" data-lang="${lang}" async></script>`;
