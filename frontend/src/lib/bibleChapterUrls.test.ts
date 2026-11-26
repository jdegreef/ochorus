import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { allBookRows } from '../test/bookRows';
import {
	BIBLE_CHAPTER_COUNTS,
	bibleBookSlugAt,
	bibleTextPath,
	bookChapterPath,
	chapterOrder,
	chapterSegment,
	isBibleBookSlug
} from './reading-schema';

const BOOKS = join(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content', 'books');
const bibleRows = () => allBookRows().filter((b) => b.series?.[0] === 'the-bible');

describe('Bible chapter URLs follow the Bible numbering', () => {
	it('Leviticus 15 is /books/leviticus/15, around an introduction and a conclusion', () => {
		expect(bookChapterPath('leviticus', 16, false)).toBe('/books/leviticus/15');
		expect(bookChapterPath('leviticus', 1, false)).toBe('/books/leviticus/introduction');
		expect(bookChapterPath('leviticus', 29, false)).toBe('/books/leviticus/conclusion');
		expect(chapterOrder('leviticus', '15')).toBe(16);
		expect(chapterOrder('leviticus', 'introduction')).toBe(1);
		expect(chapterOrder('leviticus', 'conclusion')).toBe(29);
	});

	it('names no chapter for a segment past the end, zero or a word', () => {
		expect(chapterOrder('leviticus', '28')).toBeNull();
		expect(chapterOrder('leviticus', '0')).toBeNull();
		expect(chapterOrder('leviticus', '01')).toBeNull();
		expect(chapterOrder('humility', 'introduction')).toBeNull();
	});

	it('leaves every other book alone', () => {
		expect(bookChapterPath('humility', 3, false)).toBe('/books/humility/3');
		expect(chapterSegment('humility', 1)).toBe('1');
		expect(chapterOrder('humility', '12')).toBe(12);
		expect(isBibleBookSlug('constructor')).toBe(false);
	});

	it('round-trips every stored order of every Bible book', () => {
		for (const [slug, n] of Object.entries(BIBLE_CHAPTER_COUNTS)) {
			for (let order = 1; order <= n + 2; order++) {
				expect(chapterOrder(slug, chapterSegment(slug, order))).toBe(order);
			}
		}
	});

	it('knows exactly the Bible books the fixture ships, in every language', () => {
		const slugs = new Set(bibleRows().map((b) => b.slug));
		expect([...slugs].sort()).toEqual(Object.keys(BIBLE_CHAPTER_COUNTS).sort());
	});

	it('holds each count to the English fixture: introduction + chapters + conclusion', () => {
		for (const [slug, n] of Object.entries(BIBLE_CHAPTER_COUNTS)) {
			const text = readFileSync(join(BOOKS, `${slug}.en.json`), 'utf8');
			const chapters = text.match(/"model":\s*"library\.chapter"/g)?.length ?? 0;
			expect(chapters, slug).toBe(n + 2);
		}
	});
});

describe('the Bible text a scripture page links to', () => {
	it('finds a book by its canonical position, whatever the scripture slug', () => {
		expect(bibleBookSlugAt(1)).toBe('genesis');
		expect(bibleBookSlugAt(43)).toBe('gospel-of-john');
		expect(bibleBookSlugAt(66)).toBe('revelation');
		expect(bibleBookSlugAt(67)).toBeNull();
		expect(bibleBookSlugAt(0)).toBeNull();
	});

	it('links a chapter to its reader page and a book to its book page', () => {
		expect(bibleTextPath(45, 8)).toBe('/books/romans/8');
		expect(bibleTextPath(19, 23)).toBe('/books/psalms/23');
		expect(bibleTextPath(45, null)).toBe('/books/romans');
		expect(bibleTextPath(45, 17)).toBeNull();
		expect(bibleTextPath(70, 1)).toBeNull();
	});

	it('numbers the books in the fixture’s canonical order', () => {
		for (const b of bibleRows().filter((r) => r.language === 'en')) {
			expect(bibleBookSlugAt(b.series_position as number)).toBe(b.slug);
		}
	});
});
