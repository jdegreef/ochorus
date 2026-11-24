import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { allBookRows } from '../test/bookRows';
import {
	BIBLE_CHAPTER_COUNTS,
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
