import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { downloadFormats, titleWithFormats } from './bookSeo';

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
		for (const l of ['en', 'es', 'sw', 'lg', 'pt', 'ar', 'hi', 'uk', 'fr', 'am']) {
			const msgs = JSON.parse(readFileSync(resolve(process.cwd(), `messages/${l}.json`), 'utf8'));
			expect(msgs.book_title_tag, l).toMatch(/ — Ochorus$/);
			expect(titleWithFormats(msgs.book_title_tag, 'EPUB'), l).not.toContain('Ochorus');
			expect(msgs.book_meta_download, l).toContain('%formats%');
		}
	});
});
