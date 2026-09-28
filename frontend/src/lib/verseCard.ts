// Read by the build script under plain Node, so this module stays import-free
// at runtime: the one import below is a type, and Node strips it.
import type { ScripturePage } from './library-public';

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

const FETCHED =
	/<script type="application\/json" data-sveltekit-fetched data-url="[^"]*\/api\/library\/scripture\/[^"]+"[^>]*>([\s\S]*?)<\/script>/;

/**
 * The scripture API response a prerendered verse page was rendered from —
 * SvelteKit inlines a load's `fetch` into the page — or null when the page
 * holds no verse to draw.
 */
export function verseData(html: string): (ScripturePage & { text: string }) | null {
	const raw = FETCHED.exec(html)?.[1];
	if (!raw) return null;
	try {
		const data = JSON.parse(JSON.parse(raw).body);
		return data.verse && data.text ? data : null;
	} catch {
		return null;
	}
}

/** The verse's size on the card, by length: a short verse reads as a headline,
 *  a long one still fits the column. Past the last step it is cut at a word. */
export function verseType(text: string): { text: string; size: number } {
	const steps: [number, number][] = [
		[60, 58],
		[110, 48],
		[170, 42],
		[260, 34],
		[360, 28]
	];
	const step = steps.find(([max]) => text.length <= max);
	if (step) return { text, size: step[1] };
	const cut = text.slice(0, 350);
	return { text: `${cut.slice(0, cut.lastIndexOf(' '))}…`, size: 28 };
}
