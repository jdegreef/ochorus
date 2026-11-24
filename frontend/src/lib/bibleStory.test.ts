import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { CANON } from './sermonCanon';
import { bibleChapterOrder } from './bible';
import {
	BIBLE_SLUGS,
	BIBLE_STORY,
	STORY_BOOK,
	STORY_PLAN_SLUG,
	canonPosition,
	storyBooks,
	storyEras,
	storyKeys
} from './bibleStory';

const BACKEND = resolve(__dirname, '../../../backend/library');
const BOOKS = `${BACKEND}/fixtures/content/books`;

/** The `the-bible` series as the fixtures commit it: slug → place and reader chapters. */
const series = new Map(
	readdirSync(BOOKS)
		.filter((f) => f.endsWith('.en.json'))
		.flatMap((f) => {
			const rows = JSON.parse(readFileSync(`${BOOKS}/${f}`, 'utf8')) as {
				model: string;
				fields: { slug?: string; series?: string[] | null; series_position?: number };
			}[];
			const book = rows[0].fields;
			if (book.series?.[0] !== 'the-bible') return [];
			const chapters = rows.filter((r) => r.model === 'library.chapter').length;
			return [[book.slug!, { position: book.series_position!, chapters }] as const];
		})
);

describe('BIBLE_SLUGS', () => {
	it('is the the-bible series in canonical order, 66 books', () => {
		expect(BIBLE_SLUGS).toHaveLength(66);
		expect(series.size).toBe(66);
		BIBLE_SLUGS.forEach((slug, i) => expect(series.get(slug)?.position, slug).toBe(i + 1));
		expect(CANON).toHaveLength(66);
	});
});

describe('BIBLE_STORY', () => {
	it('has 12–15 eras and unique ids', () => {
		const eras = storyEras();
		expect(eras.length).toBeGreaterThanOrEqual(12);
		expect(eras.length).toBeLessThanOrEqual(15);
		const ids = BIBLE_STORY.map((s) => s.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('links only Bible books, each section in canonical order', () => {
		for (const s of BIBLE_STORY) {
			const positions = s.books.map((slug) => canonPosition(slug));
			expect(positions.every((p) => p != null), s.id).toBe(true);
			expect(positions, s.id).toEqual([...positions].sort((a, b) => a! - b!));
		}
	});

	it('gives every era books and one or two key chapters; only the interlude has none', () => {
		for (const s of BIBLE_STORY) {
			if (s.interlude) {
				expect(s.books, s.id).toEqual([]);
				expect(s.keys, s.id).toEqual([]);
				continue;
			}
			expect(s.books.length, s.id).toBeGreaterThan(0);
			expect(s.keys.length, s.id).toBeGreaterThanOrEqual(1);
			expect(s.keys.length, s.id).toBeLessThanOrEqual(2);
		}
	});

	it('keys a chapter that exists, in a book the section links', () => {
		for (const s of BIBLE_STORY) {
			for (const k of s.keys) {
				expect(s.books, `${s.id}: ${k.slug}`).toContain(k.slug);
				const book = series.get(k.slug)!;
				// The reader's chapters less the introduction and conclusion.
				expect(k.chapter, `${s.id}: ${k.slug} ${k.chapter}`).toBeGreaterThanOrEqual(1);
				expect(k.chapter, `${s.id}: ${k.slug} ${k.chapter}`).toBeLessThanOrEqual(book.chapters - 2);
			}
		}
	});

	it('walks every one of the 66 books somewhere', () => {
		const linked = new Set(BIBLE_STORY.flatMap((s) => s.books));
		expect(BIBLE_SLUGS.filter((slug) => !linked.has(slug))).toEqual([]);
	});

	it('runs in story order: Genesis first, the Old Testament before the New, Revelation last', () => {
		expect(BIBLE_STORY[0].books).toEqual(['genesis']);
		expect(BIBLE_STORY.at(-1)!.books).toEqual(['revelation']);
		const testaments = BIBLE_STORY.map((s) => s.testament);
		const firstNew = testaments.indexOf('new');
		expect(testaments.slice(0, firstNew).every((t) => t === 'old')).toBe(true);
		expect(testaments.slice(firstNew).every((t) => t === 'new')).toBe(true);
		// Every Old Testament book's section precedes every New Testament one.
		for (const s of BIBLE_STORY) {
			const nt = s.books.some((slug) => canonPosition(slug)! >= 40);
			expect(nt, s.id).toBe(s.testament === 'new' && s.books.length > 0);
		}
		// The Genesis eras come in the book's own order.
		const genesisKeys = BIBLE_STORY.flatMap((s) =>
			s.keys.filter((k) => k.slug === 'genesis').map((k) => k.chapter)
		);
		expect(genesisKeys).toEqual([...genesisKeys].sort((a, b) => a - b));
	});

	it('keeps each era to a few sentences, quoting no Scripture', () => {
		for (const s of BIBLE_STORY) {
			const sentences = s.prose.split(/(?<=[.!?])\s+/).length;
			expect(sentences, s.id).toBeLessThanOrEqual(s.interlude ? 1 : 3);
			// A quotation would have to be the OWB's exact wording; there is none.
			expect(s.prose, s.id).not.toMatch(/[“"]/);
		}
	});
});

describe('links', () => {
	it('names books as the canon does and opens key chapters past the introduction', () => {
		const kings = BIBLE_STORY.find((s) => s.id === 'kings')!;
		expect(storyBooks(kings)[0]).toEqual({ label: '1 Samuel', href: '/books/1-samuel' });
		expect(storyKeys(kings)[0]).toEqual({
			label: '2 Samuel 7',
			href: '/books/2-samuel/7'
		});
		expect(bibleChapterOrder(7)).toBe(8);
	});

	it('cross-links a plan and a book that exist', () => {
		const seed = readFileSync(`${BACKEND}/plan_seed.py`, 'utf8');
		expect(seed).toContain(`"${STORY_PLAN_SLUG}"`);
		const book = JSON.parse(readFileSync(`${BOOKS}/${STORY_BOOK.slug}.en.json`, 'utf8'));
		expect(book[0].fields.title).toBe(STORY_BOOK.title);
	});
});
