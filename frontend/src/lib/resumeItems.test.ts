import { beforeEach, describe, it, expect } from 'vitest';
import { buildResumeItems } from './resumeItems';
import { PROGRESS_KEY } from './reading-schema';
import type { BookSummary, SermonSummary } from './library-public';

// Only the fields buildResumeItems reads; the rest of the summary is irrelevant.
const book = (slug: string, title: string, chapter_count: number): BookSummary =>
	({ slug, title, chapter_count, author: { name: `${title} author` } }) as unknown as BookSummary;
const sermon = (slug: string, title: string, scripture_ref: string): SermonSummary =>
	({ slug, title, scripture_ref, author: { name: `${title} author` } }) as unknown as SermonSummary;

beforeEach(() => localStorage.clear());

describe('buildResumeItems', () => {
	it('is empty with no progress', () => {
		expect(buildResumeItems([book('a', 'A', 3)], [])).toEqual([]);
	});

	it('resolves books and sermons newest-first, dropping slugs with no catalog row', () => {
		localStorage.setItem(
			PROGRESS_KEY,
			JSON.stringify({
				'waiting-on-god': { order: 27, paragraph_index: 0, language: 'en', at: 3 },
				'sermon:power-of-stillness': { order: 1, paragraph_index: 4, language: 'en', at: 4 },
				humility: { order: 6, paragraph_index: 0, language: 'en', at: 2 },
				'ghost-book': { order: 1, paragraph_index: 0, language: 'en', at: 5 } // newest, but unknown
			})
		);
		const items = buildResumeItems(
			[book('waiting-on-god', 'Waiting on God', 35), book('humility', 'Humility', 6)],
			[sermon('power-of-stillness', 'The Power of Stillness', '1 Kings 19:12')]
		);
		// ghost-book has no row in the catalogs → dropped, not shown as a slug; the
		// rest are newest-first by `at`.
		expect(items.map((i) => i.key)).toEqual([
			'sermon:power-of-stillness', // at 4
			'waiting-on-god', // at 3 (books keep their bare storage key)
			'humility' // at 2
		]);
	});

	it('flags a book on its last chapter as finished; a sermon never is', () => {
		localStorage.setItem(
			PROGRESS_KEY,
			JSON.stringify({
				humility: { order: 6, paragraph_index: 0, language: 'en', at: 2 },
				'waiting-on-god': { order: 27, paragraph_index: 0, language: 'en', at: 3 },
				'sermon:power-of-stillness': { order: 1, paragraph_index: 0, language: 'en', at: 4 }
			})
		);
		const by = Object.fromEntries(
			buildResumeItems(
				[book('humility', 'Humility', 6), book('waiting-on-god', 'Waiting on God', 35)],
				[sermon('power-of-stillness', 'The Power of Stillness', '')]
			).map((i) => [i.key, i])
		);
		expect(by['humility'].finished).toBe(true); // order 6 of 6
		expect(by['waiting-on-god'].finished).toBe(false); // order 27 of 35
		expect(by['sermon:power-of-stillness'].finished).toBe(false);
	});

	it('builds a chapter deep-link and meter for books, and a ref for sermons', () => {
		localStorage.setItem(
			PROGRESS_KEY,
			JSON.stringify({
				'waiting-on-god': { order: 27, paragraph_index: 0, language: 'en', at: 3 },
				'sermon:power-of-stillness': { order: 1, paragraph_index: 4, language: 'en', at: 4 }
			})
		);
		const [sm, bk] = buildResumeItems(
			[book('waiting-on-god', 'Waiting on God', 35)],
			[sermon('power-of-stillness', 'The Power of Stillness', '1 Kings 19:12')]
		);
		// Book: deep-links to the open chapter and carries the meter + caption fields
		// (WorkCard composes the line "Chapter 27 / 35 · N%" from these).
		expect(bk.href).toBe('/books/waiting-on-god/27');
		expect(bk.book).toBeDefined();
		expect(bk.pct).toBeGreaterThan(0);
		expect(bk.pct).toBeLessThanOrEqual(100);
		expect(bk.chapterCount).toBe(35);
		expect(bk.order).toBe(27);
		// Sermon: resumes at its paragraph, has no meter, carries its reference.
		expect(sm.href).toBe('/sermons/power-of-stillness?p=4');
		expect(sm.book).toBeUndefined();
		expect(sm.pct).toBeNull();
		expect(sm.scriptureRef).toBe('1 Kings 19:12');
	});
});
