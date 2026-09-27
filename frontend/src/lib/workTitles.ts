import { readJSON } from './persisted';
import {
	BOOKMARKS_KEY,
	FAVORITES_KEY,
	MARKS_KEY,
	PROGRESS_KEY,
	workSlugKey,
	type WorkKind
} from './reading-schema';
import { listArticlesWithFallback, listAuthors, listBooks, listSermons } from './library-public';

export type WorkMeta = { title: string; author: string };
export type WorkTitles = Record<WorkKind, Map<string, WorkMeta>>;

/** Turn a slug into a passable label when the catalog lookup misses. */
export function unslug(slug: string): string {
	return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Whether anything this device keeps (progress, marks, bookmarks, favorites)
 *  names an article — every key of all four is prefixed by its kind. */
function storesMentionArticles(): boolean {
	const prefix = workSlugKey('article', '');
	return [PROGRESS_KEY, MARKS_KEY, BOOKMARKS_KEY, FAVORITES_KEY].some((k) =>
		Object.keys(readJSON<Record<string, unknown>>(k, {})).some((key) => key.startsWith(prefix))
	);
}

/**
 * Title + author for every work of every kind, keyed by slug — the catalogue
 * "Your reading" and the data export both resolve a stored slug against.
 * Best-effort: a failed list is an empty map, and the caller falls back to
 * `unslug`. The article list is two requests (own language + English), so it
 * is fetched only when this device holds something of an article's.
 */
export async function loadWorkTitles(language: string): Promise<WorkTitles> {
	const [books, sermons, authors, articles] = await Promise.all([
		listBooks(language).catch(() => []),
		listSermons(language).catch(() => []),
		listAuthors(language).catch(() => []),
		storesMentionArticles() ? listArticlesWithFallback(language) : []
	]);
	return {
		book: new Map(books.map((b) => [b.slug, { title: b.title, author: b.author?.name ?? '' }])),
		sermon: new Map(sermons.map((s) => [s.slug, { title: s.title, author: s.author?.name ?? '' }])),
		// A "bio" work is keyed by the author's slug; its title is the author's name.
		bio: new Map(authors.map((a) => [a.slug, { title: a.name, author: a.name }])),
		// An article's byline is the house, so it names no author.
		article: new Map(articles.map((a) => [a.slug, { title: a.h1, author: '' }]))
	};
}
