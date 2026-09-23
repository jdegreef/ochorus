import { describe, expect, it } from 'vitest';
import { deriveHomeShelves } from './homeShelves';
import type { AuthorBio, BookSummary, TopicSummary } from './library-public';

const book = (slug: string, author: string, cover = `/covers/art/${slug}.jpg`) =>
	({ slug, title: slug, cover_url: cover, author: { slug: author, name: author } }) as BookSummary;
const author = (slug: string, book_count: number) =>
	({ slug, name: slug, book_count }) as AuthorBio;
const topic = (title: string, book_count: number, sermon_count = 0) =>
	({ slug: title, title, book_count, sermon_count }) as TopicSummary;

const books = Array.from({ length: 20 }, (_, i) => book(`b${i}`, `a${i % 10}`));
const lists = (over: Partial<Parameters<typeof deriveHomeShelves>[0]> = {}) => ({
	books,
	authors: Array.from({ length: 12 }, (_, i) => author(`a${i}`, i)),
	topics: Array.from({ length: 12 }, (_, i) => topic(`t${i}`, i)),
	sermons: [1, 2, 3],
	...over
});

describe('deriveHomeShelves', () => {
	it('is a pure function of the lists and the day', () => {
		// The property the snapshot exists for: the same inputs give the same
		// six, so the prerendered HTML and its replay can never disagree.
		expect(deriveHomeShelves(lists(), 20000)).toEqual(deriveHomeShelves(lists(), 20000));
	});

	it('features six books by six different authors, never a plate cover', () => {
		// Authors a0–a2 wear only plate covers; seven authors remain to pick from.
		const plates = books.map((b, i) => (i % 10 < 3 ? { ...b, cover_url: `/covers/${b.slug}.svg` } : b));
		const { featured } = deriveHomeShelves(lists({ books: plates }), 20000);
		expect(featured).toHaveLength(6);
		expect(featured.every((b) => !b.cover_url.endsWith('.svg'))).toBe(true);
		expect(new Set(featured.map((b) => b.author.slug)).size).toBe(featured.length);
	});

	it('shows the eight most-published authors with a book, and the eight richest topics', () => {
		const { authors, topics } = deriveHomeShelves(lists(), 20000);
		expect(authors.map((a) => a.slug)).toEqual(['a11', 'a10', 'a9', 'a8', 'a7', 'a6', 'a5', 'a4']);
		expect(topics.map((t) => t.title)).toEqual(['t11', 't10', 't9', 't8', 't7', 't6', 't5', 't4']);
	});

	it('carries only the fields the home page draws', () => {
		// The snapshot is inlined into every locale's front page, so a bio or a
		// topic's cover list riding along is weight on the critical path.
		const withExtras = lists({
			books: books.map((b) => ({ ...b, topics: [], created_at: 'x', author: { ...b.author, bio: 'long' } })),
			authors: lists().authors.map((a) => ({ ...a, bio: 'long', has_long_bio: true })),
			topics: lists().topics.map((t) => ({ ...t, description: 'long', covers: [] }))
		});
		const { featured, authors, topics } = deriveHomeShelves(withExtras, 20000);
		expect(Object.keys(featured[0])).not.toContain('topics');
		expect(Object.keys(featured[0])).not.toContain('created_at');
		expect(Object.keys(featured[0].author)).not.toContain('bio');
		expect(Object.keys(authors[0]).sort()).toEqual(['book_count', 'name', 'photo_url', 'slug']);
		expect(Object.keys(topics[0]).sort()).toEqual(['book_count', 'sermon_count', 'slug', 'title']);
	});

	it('passes a field added to BookSummary through to the home cards by default', () => {
		// The book projection lists what to DROP, so a new field reaches the
		// cards without anyone remembering the home page projects.
		const withNew = lists({ books: books.map((b) => ({ ...b, edition_label: 'x' })) });
		const [first] = deriveHomeShelves(withNew, 20000).featured;
		expect((first as unknown as { edition_label: string }).edition_label).toBe('x');
	});

	it("counts the language's whole library, not the capped shelves", () => {
		expect(deriveHomeShelves(lists(), 20000).counts).toEqual({ books: 20, authors: 12, sermons: 3 });
	});
});
