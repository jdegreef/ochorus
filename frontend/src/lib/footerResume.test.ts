import { describe, expect, it } from 'vitest';
import { pageShowsBook } from './footerResume';

describe('pageShowsBook', () => {
	it('is true where the page already shows the current book', () => {
		for (const p of ['/', '/reading', '/reading/', '/favorites', '/books/pursuit-of-god', '/books/pursuit-of-god/', '/books/pursuit-of-god/4'])
			expect(pageShowsBook(p, 'pursuit-of-god'), p).toBe(true);
	});

	it('is false elsewhere, including another book and a slug that only shares a prefix', () => {
		for (const p of ['/topics/', '/books/', '/books/confessions/2', '/books/pursuit-of-god-2/1', '/sermons/x/'])
			expect(pageShowsBook(p, 'pursuit-of-god'), p).toBe(false);
	});
});
