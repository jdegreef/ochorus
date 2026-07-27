import { describe, expect, it } from 'vitest';
import { withTrailingSlash } from './href';

describe('withTrailingSlash', () => {
	it('adds the slash to detail pages, which is the whole point', () => {
		expect(withTrailingSlash('/books/the-inner-chamber')).toBe('/books/the-inner-chamber/');
		expect(withTrailingSlash('/authors/andrew-murray')).toBe('/authors/andrew-murray/');
		expect(withTrailingSlash('/topics/prayer')).toBe('/topics/prayer/');
		expect(withTrailingSlash('/sermons/free-grace')).toBe('/sermons/free-grace/');
		expect(withTrailingSlash('/plans/humility')).toBe('/plans/humility/');
	});

	it('handles the chapter route (one segment deeper)', () => {
		expect(withTrailingSlash('/books/the-inner-chamber/12')).toBe('/books/the-inner-chamber/12/');
	});

	it('keeps the locale prefix and still matches the shape', () => {
		expect(withTrailingSlash('/es/books/the-inner-chamber')).toBe('/es/books/the-inner-chamber/');
		expect(withTrailingSlash('/sw/authors/andrew-murray')).toBe('/sw/authors/andrew-murray/');
		expect(withTrailingSlash('/lg/books/humility/3')).toBe('/lg/books/humility/3/');
	});

	it('is idempotent — never doubles the slash', () => {
		expect(withTrailingSlash('/books/humility/')).toBe('/books/humility/');
		expect(withTrailingSlash(withTrailingSlash('/books/humility'))).toBe('/books/humility/');
	});

	it('preserves query strings and hashes, slash before them', () => {
		expect(withTrailingSlash('/books/humility?from=home')).toBe('/books/humility/?from=home');
		expect(withTrailingSlash('/books/humility#chapter-2')).toBe('/books/humility/#chapter-2');
		expect(withTrailingSlash('/search?q=prayer')).toBe('/search?q=prayer');
	});

	it('leaves index pages alone — they resolve either way via Render rewrites', () => {
		expect(withTrailingSlash('/books')).toBe('/books');
		expect(withTrailingSlash('/biographies')).toBe('/biographies');
		expect(withTrailingSlash('/es/books')).toBe('/es/books');
		expect(withTrailingSlash('/')).toBe('/');
	});

	it('leaves non-detail and client-only routes alone', () => {
		expect(withTrailingSlash('/admin/books/humility')).toBe('/admin/books/humility');
		expect(withTrailingSlash('/settings')).toBe('/settings');
		expect(withTrailingSlash('/notebook')).toBe('/notebook');
	});

	it('never touches files or external links', () => {
		expect(withTrailingSlash('/covers/humility.svg')).toBe('/covers/humility.svg');
		expect(withTrailingSlash('/books/humility/cover.jpg')).toBe('/books/humility/cover.jpg');
		expect(withTrailingSlash('https://example.com/books/x')).toBe('https://example.com/books/x');
		expect(withTrailingSlash('mailto:support@ochorus.com')).toBe('mailto:support@ochorus.com');
		expect(withTrailingSlash('#era-early')).toBe('#era-early');
	});

	it('ignores paths deeper than the known shapes', () => {
		expect(withTrailingSlash('/books/a/b/c')).toBe('/books/a/b/c');
	});
});
