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
 * The snippet itself is shown to church leaders on the /for/ pages, with a
 * plain-`<iframe>` alternative for website builders that strip `<script>`
 * tags, and the card itself as a live preview (EmbedToday, drawn inline — no
 * frame, so the site's own CSP needs no `frame-src` for it).
 *
 * Links are plain ochorus.com URLs, no UTM or `?ref=`: the iframe's pageview
 * already carries the church's site as its referrer, and a click opens a
 * same-site tab that continues that visit, so the analytics see where it came
 * from without tagging the URL. Clicks are also counted as `EMBED_EVENT`.
 */

/** Route ids drawn as a bare widget: no nav, footer, tab bar or prompts. */
export const isEmbedRoute = (routeId: string | null | undefined): boolean =>
	!!routeId?.startsWith('/embed/');

/**
 * Whether a URL path is one render.yaml lets other sites frame:
 * `[/<lang>]/embed/…`. Unlike {@link isEmbedRoute} it also holds for a path
 * no route matches (a 404 under /embed/ is still a framed document), and the
 * root layout checks it to keep a framed document from turning, client-side,
 * into the full site inside a church's page.
 */
export const isEmbedPath = (pathname: string): boolean => /^(\/[a-z]{2,3})?\/embed(\/|$)/.test(pathname);

/** What the iframe's `?theme=` asks for, as a theme preference: `dark`,
 *  `sepia`, `auto` (the visitor's OS setting) or, by default, `light`. */
export function embedTheme(param: string | null): ThemePref {
	if (param === 'auto' || param === 'system') return 'system';
	return (EMBED_THEMES as readonly (string | null)[]).includes(param) ? (param as ThemePref) : 'light';
}

/** The looks a church can ask for, as embed.js's `data-theme` / the
 *  iframe's `?theme=`. */
export const EMBED_THEMES = ['light', 'dark', 'sepia', 'auto'] as const;
export type EmbedTheme = (typeof EMBED_THEMES)[number];

/** The page the widget's iframe shows, exactly as embed.js builds it: the
 *  locale prefix (none for English), and `?theme=` only when not light. */
export const embedUrl = (siteUrl: string, lang: string, theme: EmbedTheme = 'light'): string =>
	`${siteUrl}${lang === 'en' ? '' : `/${lang}`}/embed/today${theme === 'light' ? '' : `?theme=${theme}`}`;

/** The Plausible event a click inside the widget sends, with the part
 *  followed (`part`: brand | reading | sermon | more). Never a URL. */
export const EMBED_EVENT = 'Church widget click';

/** The `postMessage` type the widget page reports its height under; embed.js
 *  listens for the same string. */
export const EMBED_HEIGHT_MESSAGE = 'ochorus:embed-height';

/** The tag a church pastes, for a widget in `lang`. */
export const embedSnippet = (siteUrl: string, lang: string): string =>
	`<script src="${siteUrl}/embed.js" data-widget="today" data-lang="${lang}" async></script>`;

/** The height the plain-iframe snippet starts at: the stacked card in a
 *  sidebar. embed.js sizes its frame to the card; a pasted iframe cannot. */
export const EMBED_FRAME_HEIGHT = 460;

/**
 * The fallback for website builders that remove `<script>` tags (many
 * church-site builders' "embed" blocks take an iframe but not a script): the
 * same page in a plain iframe, sandboxed and styled as embed.js's own: with
 * a `color-scheme` matching the page inside (light, by default), or the
 * browser paints the frame opaque around the card's rounded corners.
 */
export const embedFrameSnippet = (siteUrl: string, lang: string): string =>
	`<iframe src="${embedUrl(siteUrl, lang)}" title="Today from Ochorus" loading="lazy" ` +
	`sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox" ` +
	`style="display:block;width:100%;max-width:100%;height:${EMBED_FRAME_HEIGHT}px;border:0;color-scheme:light"></iframe>`;
