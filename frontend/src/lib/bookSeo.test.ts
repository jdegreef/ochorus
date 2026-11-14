import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
	bibleChapterMeta,
	bibleChapterTitle,
	chapterMeta,
	distinctTitle,
	downloadFormats,
	isBibleChapter,
	titleWithFormats
} from './bookSeo';

describe('downloadFormats', () => {
	it('names what the edition offers, in search order', () => {
		expect(downloadFormats({ pdf_url: '/pdfs/x.pdf', epub_url: '/api/x.epub' })).toBe('PDF & EPUB');
		expect(downloadFormats({ pdf_url: '', epub_url: '/api/x.epub' })).toBe('EPUB');
		expect(downloadFormats({ pdf_url: '/pdfs/x.pdf' })).toBe('PDF');
		expect(downloadFormats({ pdf_url: '', epub_url: '' })).toBe('');
	});
});

describe('titleWithFormats', () => {
	const title = 'The Pursuit of God by A. W. Tozer — read free online — Ochorus';

	it('trades the brand suffix for the formats', () => {
		expect(titleWithFormats(title, 'PDF & EPUB')).toBe(
			'The Pursuit of God by A. W. Tozer — read free online (PDF & EPUB)'
		);
	});

	it('leaves a book with no download alone', () => {
		expect(titleWithFormats(title, '')).toBe(title);
	});

	it("fits every locale's title template", () => {
		// The suffix it strips must be how each catalogue actually ends the title.
		for (const l of ['en', 'es', 'sw', 'lg', 'pt', 'ar', 'hi', 'uk', 'fr', 'am', 'vi', 'ko', 'ja', 'ru']) {
			const msgs = JSON.parse(readFileSync(resolve(process.cwd(), `messages/${l}.json`), 'utf8'));
			expect(msgs.book_title_tag, l).toMatch(/ — Ochorus$/);
			expect(titleWithFormats(msgs.book_title_tag, 'EPUB'), l).not.toContain('Ochorus');
			expect(msgs.book_meta_download, l).toContain('%formats%');
		}
	});
});

describe('distinctTitle', () => {
	const title = 'The Holy Spirit, or Power from on High';
	it('adds the subtitle when the series is named exactly as the volume', () => {
		expect(
			distinctTitle({ title, subtitle: 'Part I: The Old Testament', series: { title } })
		).toBe(`${title}: Part I: The Old Testament`);
	});
	it('keeps the plain title otherwise', () => {
		expect(distinctTitle({ title, subtitle: 'Part I', series: { title: 'Rooted' } })).toBe(title);
		expect(distinctTitle({ title, subtitle: 'Part I', series: null })).toBe(title);
		expect(distinctTitle({ title, subtitle: '', series: { title } })).toBe(title);
	});
});

describe('chapterMeta', () => {
	it('leads with book and chapter, so shared openings still differ', () => {
		const opening = ' “I passed by the field of a sluggard…” ';
		const a = chapterMeta('Talks to the Farmer', 'Chapter 1', opening);
		const b = chapterMeta('Talks to the Farmer (Teens)', 'Chapter 1', opening);
		expect(a).toBe('Talks to the Farmer — Chapter 1: “I passed by the field of a sluggard…”');
		expect(a).not.toBe(b);
	});
	it('drops the colon when the chapter has no text', () => {
		expect(chapterMeta('Book', 'Chapter 2', '  ')).toBe('Book — Chapter 2');
	});
});

describe('Bible chapters', () => {
	const owb = (title: string) => ({ author_slug: 'open-word-bible', title });

	it('are the numbered chapters of the Open Word Bible’s books, not their introductions', () => {
		expect(isBibleChapter(owb('Psalm 23'))).toBe(true);
		expect(isBibleChapter(owb('John 3'))).toBe(true);
		expect(isBibleChapter(owb('1 Corinthians 13'))).toBe(true);
		expect(isBibleChapter(owb('Song of Songs 2'))).toBe(true);
		expect(isBibleChapter(owb('Introduction'))).toBe(false);
		expect(isBibleChapter(owb('Conclusion'))).toBe(false);
		// Another writer's numbered chapter is not Scripture.
		expect(isBibleChapter({ author_slug: 'andrew-murray', title: 'Day 3' })).toBe(false);
	});

	it('are titled the way they are searched for', () => {
		expect(bibleChapterTitle('Psalm 23', 'Open Word Bible')).toBe('Psalm 23 — Open Word Bible — Ochorus');
	});

	it('are described by their summary, chapter first', () => {
		expect(bibleChapterMeta('Romans 8', 'Open Word Bible', ' There is no condemnation. ')).toBe(
			'Romans 8 (Open Word Bible): There is no condemnation.'
		);
		expect(bibleChapterMeta('Malachi 4', 'Open Word Bible', '')).toBe('Malachi 4 (Open Word Bible)');
	});
});
