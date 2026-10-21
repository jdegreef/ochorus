/**
 * A prerendered chapter page carries its prose ONCE.
 *
 * Hydration re-runs the page's load in the browser, and SvelteKit feeds that
 * second run by inlining every response the prerender's load read into the
 * HTML (`<script data-sveltekit-fetched>`, see `Fetch` in $lib/api). For a
 * chapter that response is almost all `body_html` — the very prose the page has
 * just rendered — so every chapter page shipped its text twice: on a long
 * chapter (sermons-on-several-occasions/5) 45 KB of the built page's 141 KB,
 * and 16 KB of its 47 KB gzipped (the copy sits further back than gzip's 32 KB
 * window, so compression saved none of it); about a third of every chapter
 * page, short ones included.
 *
 * So the build reads the chapter WITHOUT recording it ({@link unrecorded}), the
 * page writes the rest of the payload — everything but the body, ~1 KB — into
 * a seed beside it ({@link chapterSeedTag}), and the hydration load rebuilds the
 * chapter from that seed plus the prose already in the DOM
 * ({@link takeChapterSeed}). No request, as before, and the page's HTML is the
 * same apart from the seed tag and the body's marker attribute.
 *
 * The body the browser hands back is its own serialization of the prerendered
 * prose — the same nodes, but `&quot;` reads `"`, `<br/>` reads `<br>`. Svelte
 * adopts the server's nodes on hydration rather than re-rendering an {@html}
 * block, so nothing on the page moves; dev mode, which hash-checks that block
 * and would warn, keeps the old inlined path (the load gates on `dev`).
 *
 * Anything unexpected — no seed (the SPA fallback, the phone app, a page built
 * before this), a seed for another URL, a seed that won't parse — returns null
 * and the load fetches as it always did.
 */

import type { Fetch } from './api';
import type { Chapter } from './library-public';

/** The seed `<script>`'s id, and the attribute marking the prose container. */
export const CHAPTER_SEED_ID = 'chapter-seed';
export const CHAPTER_BODY_ATTR = 'data-chapter-body';

interface Seed {
	/** The page the seed was rendered for, without its trailing slash. */
	path: string;
	/** The language the body is in (getChapterWithLang's resolved one). */
	language: string;
	chapter: Omit<Chapter, 'body_html'>;
}

const pathKey = (pathname: string) => pathname.replace(/\/+$/, '');

/**
 * A load `fetch` whose responses SvelteKit does not inline. Its fetch records a
 * response when the body is read through `text`/`json`/`arrayBuffer`/`body`;
 * a `clone()` is a plain Response it never sees read. Should SvelteKit start
 * recording clones, the only effect is the old duplicate coming back — the
 * hydration load still prefers the seed.
 */
export const unrecorded =
	(f: Fetch): Fetch =>
	async (input, init) =>
		(await f(input, init)).clone();

/** The seed for `<svelte:head>`, via {@html}: the payload minus the body.
 *  `<` is escaped so chapter text can never close the script early. */
export function chapterSeedTag(chapter: Chapter, language: string, pathname: string): string {
	const { body_html: _body, ...rest } = chapter;
	const seed: Seed = { path: pathKey(pathname), language, chapter: rest };
	const json = JSON.stringify(seed).replace(/</g, '\\u003c');
	return `<script type="application/json" id="${CHAPTER_SEED_ID}">${json}</script>`;
}

/**
 * The prose an {@html} block rendered, as the prerendered DOM holds it: Svelte
 * brackets the block with a `<!--hash-->` comment and an empty `<!---->` one,
 * which are hydration markers, not prose (the sanitized body has no comments).
 */
export const proseHtml = (container: Element) =>
	container.innerHTML.replace(/^<!--[^>]*?-->/, '').replace(/<!---->$/, '');

let taken = false;

/**
 * The chapter the prerendered page was built from — only on the document's
 * FIRST call (the hydration load; after it the DOM is the app's, and another
 * chapter's seed may still be in it), and only when the seed names this page.
 */
export function takeChapterSeed(
	pathname: string,
	doc: Document = document
): { data: Chapter; language: string } | null {
	if (taken) return null;
	taken = true;
	try {
		const seed = JSON.parse(doc.getElementById(CHAPTER_SEED_ID)?.textContent ?? 'null') as Seed | null;
		const body = doc.querySelector(`[${CHAPTER_BODY_ATTR}]`);
		if (!seed || !body || seed.path !== pathKey(pathname)) return null;
		return { data: { ...seed.chapter, body_html: proseHtml(body) } as Chapter, language: seed.language };
	} catch {
		return null;
	}
}

/** Tests only: forget that the first call happened. */
export function resetChapterSeed() {
	taken = false;
}
