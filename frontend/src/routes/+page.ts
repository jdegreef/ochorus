import { building } from '$app/environment';
import { listBooks, listAuthors, listTopics } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

/**
 * Tolerate a failed shelf at RUNTIME, never while building.
 *
 * The two contexts want opposite things from the same error. During the build
 * a swallowed failure is the worst outcome available: the homepage prerenders
 * with an empty shelf, ships, and looks deliberate — nothing is red, and the
 * site simply has no books on its front page until someone notices. At runtime
 * — a client-side navigation home, a reader who has gone offline — throwing
 * replaces a page whose chrome, nav and personal blocks all still work with a
 * full-page error. So: loud at build time, degraded at run time.
 */
const shelf = <T>(pending: Promise<T[]>): Promise<T[]> =>
	building ? pending : pending.catch(() => []);

// NOTE: this page is prerendered — only PUBLIC data belongs here. Personal
// blocks (Continue reading, Today's reading) fetch client-side in their
// components so the baked HTML is the same for everyone.
export const load: PageLoad = async () => {
	const [books, authors, topics] = await Promise.all([
		shelf(listBooks(getLang())),
		shelf(listAuthors()),
		// Topics stay tolerant even during the build: they are a decorative
		// cross-navigation row, and the page below already hides the section
		// when there are none.
		listTopics(getLang()).catch(() => [])
	]);
	return {
		books,
		featured: books.slice(0, 6),
		totalBooks: books.length,
		authors: authors.filter((a) => a.book_count > 0),
		topics: topics.filter((topic) => topic.book_count > 0)
	};
};
