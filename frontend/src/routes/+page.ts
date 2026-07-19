import { listBooks, listAuthors, listTopics } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import type { PageLoad } from './$types';

// NOTE: this page is prerendered — only PUBLIC data belongs here. Personal
// blocks (Continue reading, Today's reading) fetch client-side in their
// components so the baked HTML is the same for everyone.
export const load: PageLoad = async () => {
	const [books, authors, topics] = await Promise.all([
		listBooks(getLang()),
		listAuthors(),
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
