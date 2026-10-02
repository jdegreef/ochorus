// Read by the build script under plain Node, so this module stays import-free
// at runtime: the one import below is a type, and Node strips it.
import type { ScriptureBookPage, ScripturePage } from './library-public';

/**
 * Where a scripture verse page's share card lives.
 *
 * Not committed: `scripts/build-verse-cards.mjs` draws one into the build for
 * every prerendered verse page, from the data that page was rendered with. Said
 * once so the page that names a card and the script that draws it cannot
 * disagree about the path.
 */
export function verseCardUrl(book: string, chapter: number, verse: number): string {
	return `/og/scripture/${book}/${chapter}/${verse}.jpg`;
}

/** Where a Bible book page's (`/scripture/<book>/`) share card lives — drawn
 *  by the same script, from the same inlined data. */
export function scriptureBookCardUrl(book: string): string {
	return `/og/scripture/${book}.jpg`;
}

/**
 * The body of the first response a prerendered page inlined (SvelteKit inlines a
 * load's `fetch`) from a scripture API URL whose path after
 * `/api/library/scripture/` matches `rest` (a RegExp source) and that answered
 * below 400, parsed; null if none. (card-kit's `inlined`, for this module's
 * type-only, import-free contract.)
 */
function inlinedScripture(html: string, rest: string): Record<string, unknown> | null {
	const re = new RegExp(
		`<script type="application/json" data-sveltekit-fetched data-url="[^"]*/api/library/scripture/${rest}"[^>]*>([\\s\\S]*?)</script>`,
		'g'
	);
	for (const [, raw] of html.matchAll(re)) {
		try {
			const response = JSON.parse(raw);
			if ((response.status ?? 200) < 400) return JSON.parse(response.body);
		} catch {
			/* not this one */
		}
	}
	return null;
}

/**
 * The scripture API response a prerendered verse page was rendered from, or
 * null when the page holds no verse to draw.
 */
export function verseData(html: string): (ScripturePage & { text: string }) | null {
	const data = inlinedScripture(html, '[^"]+');
	return data?.verse && data.text ? (data as unknown as ScripturePage & { text: string }) : null;
}

/** The book response (`/api/library/scripture/<book>/`) a prerendered
 *  `/scripture/<book>/` page inlines, or null when it holds none — a page built
 *  from the page list fetches globally, so nothing is inlined, and its card
 *  falls back to the Scripture card. */
export function scriptureBookData(html: string): ScriptureBookPage | null {
	const data = inlinedScripture(html, '[^/"]+/');
	const book = data?.book as { title?: string } | undefined;
	return book?.title && Array.isArray(data?.chapters) ? (data as unknown as ScriptureBookPage) : null;
}

/** The verse's size on the card, by length: a short verse reads as a headline,
 *  a long one still fits the column. Past the last step it is cut at a word. */
export function verseType(text: string): { text: string; size: number } {
	const steps: [number, number][] = [
		[60, 58],
		[110, 48],
		[170, 42],
		[230, 34],
		[360, 28]
	];
	const step = steps.find(([max]) => text.length <= max);
	if (step) return { text, size: step[1] };
	const cut = text.slice(0, 350);
	return { text: `${cut.slice(0, cut.lastIndexOf(' '))}…`, size: 28 };
}
