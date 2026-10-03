import { describe, it, expect } from 'vitest';
import { scriptureBookCardUrl, scriptureBookData, verseCardUrl, verseData, verseType } from './verseCard';

const inlined = (url: string, body: unknown) =>
	`<script type="application/json" data-sveltekit-fetched data-url="${url}" data-hash="1">` +
	JSON.stringify({ status: 200, statusText: '', headers: {}, body: JSON.stringify(body) }) +
	'</script>';

describe('verse share card', () => {
	it('lives at one path per verse', () => {
		expect(verseCardUrl('john', 3, 16)).toBe('/og/scripture/john/3/16.jpg');
	});

	it('reads the scripture response a prerendered verse page inlines', () => {
		const page = { reference: 'John 3:16', verse: 16, text: 'For God so loved…', passages: [] };
		const html = inlined('https://api.ochorus.com/api/library/scripture/john/3/16/', page);
		expect(verseData(`<head></head>${html}`)).toEqual(page);
	});

	it('declines a page without a verse to draw — the card falls back, the build goes on', () => {
		expect(verseData('<html></html>')).toBeNull();
		const chapter = inlined('https://api.ochorus.com/api/library/scripture/john/3/', {
			verse: null,
			text: undefined
		});
		expect(verseData(chapter)).toBeNull();
		const other = inlined('https://api.ochorus.com/api/library/books/', { verse: 1, text: 'x' });
		expect(verseData(other)).toBeNull();
	});

	it('sets a short verse large and a long one small', () => {
		expect(verseType('Jesus wept.').size).toBeGreaterThan(verseType('x'.repeat(300)).size);
	});

	it('cuts a verse past the column at a word, never mid-word', () => {
		const long = Array.from({ length: 80 }, (_, i) => `word${i}`).join(' ');
		const { text } = verseType(long);
		expect(text.endsWith('…')).toBe(true);
		expect(long.startsWith(text.slice(0, -1))).toBe(true);
		expect(long[text.length - 1]).toBe(' ');
	});
});

describe('Bible book share card', () => {
	it('lives beside its verse cards, one per book', () => {
		expect(scriptureBookCardUrl('romans')).toBe('/og/scripture/romans.jpg');
	});

	it('reads the book response a prerendered book page inlines', () => {
		const page = { book: { slug: 'romans', title: 'Romans', order: 45 }, chapters: [], top_books: [] };
		const html = inlined('https://api.ochorus.com/api/library/scripture/romans/', page);
		expect(scriptureBookData(html)).toEqual(page);
	});

	it('declines a page with no book inlined — built from the page list, it falls back', () => {
		expect(scriptureBookData('<html></html>')).toBeNull();
		const verse = inlined('https://api.ochorus.com/api/library/scripture/john/3/16/', { verse: 16, text: 'x' });
		expect(scriptureBookData(verse)).toBeNull();
	});

	it('skips an inlined error response for the next good one', () => {
		const page = { book: { slug: 'romans', title: 'Romans', order: 45 }, chapters: [] };
		const failed =
			'<script type="application/json" data-sveltekit-fetched data-url="https://api.ochorus.com/api/library/scripture/romans/" data-hash="1">' +
			JSON.stringify({ status: 404, statusText: '', headers: {}, body: JSON.stringify({ book: { title: 'x' }, chapters: [] }) }) +
			'</script>';
		expect(scriptureBookData(failed)).toBeNull();
		expect(scriptureBookData(failed + inlined('https://api.ochorus.com/api/library/scripture/romans/', page))).toEqual(page);
	});
});
