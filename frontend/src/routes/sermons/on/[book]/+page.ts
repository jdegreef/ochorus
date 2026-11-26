import { error } from '@sveltejs/kit';
import { listSermons } from '$lib/library-public';
import { getLang } from '$lib/lang.svelte';
import { sermonsOnBooks, sermonsOnPosition, sermonsOnSlug } from '$lib/sermonsOn';
import type { EntryGenerator, PageLoad } from './$types';

// Trailing-slash canonical -> prerenders to sermons/on/<book>/index.html, served
// as a directory index by the static host (see books/[slug] for the full note).
export const trailingSlash = 'always';

// One page per book of the Bible that at least SERMONS_ON_FLOOR English sermons
// preach from ($lib/sermonsOn). Another locale's pages are reached by the crawl,
// through links that check the same floor against that locale's sermons. An API
// lagging this deploy degrades to no pages rather than failing the build.
export const entries: EntryGenerator = async () => {
	try {
		return sermonsOnBooks(await listSermons('en')).map((p) => ({ book: sermonsOnSlug(p)! }));
	} catch {
		return [];
	}
};

export const load: PageLoad = async ({ params }) => {
	const position = sermonsOnPosition(params.book);
	if (position == null) throw error(404, 'Not found');
	// Global fetch, not the load's: the prerender would inline the whole shelf
	// into the page. Only what the page draws is returned below.
	const all = await listSermons(getLang());
	const positions = sermonsOnBooks(all);
	if (!positions.includes(position)) throw error(404, 'Not found');
	// This book's sermons, and a name for each other book with a page, to link.
	const names = new Map(all.map((s) => [s.scripture_book_order, s.scripture_book]));
	return {
		position,
		sermons: all.filter((s) => s.scripture_book_order === position),
		books: positions.map((p) => ({ position: p, name: names.get(p) ?? '' }))
	};
};
