import { describe, expect, it } from 'vitest';
import { isFilePath, linkTarget } from './links';

const SITE = 'https://ochorus.com';
const IOS = 'capacitor://localhost/books/humility/';
const ANDROID = 'https://localhost/es/books/';

describe('isFilePath', () => {
	it('names files, not reader pages', () => {
		expect(isFilePath('/feed.xml')).toBe(true);
		expect(isFilePath('/sitemap-books.xml')).toBe(true);
		expect(isFilePath('/pdfs/humility.pdf')).toBe(true);
		expect(isFilePath('/robots.txt')).toBe(true);
		expect(isFilePath('/books/humility/')).toBe(false);
		expect(isFilePath('/books/humility')).toBe(false);
		expect(isFilePath('/')).toBe(false);
		expect(isFilePath('/about.html')).toBe(false);
	});
});

describe('linkTarget', () => {
	it('leaves the app’s own pages to the router (iOS custom scheme too)', () => {
		expect(linkTarget('/books/', IOS, SITE)).toBeNull();
		expect(linkTarget('../', IOS, SITE)).toBeNull();
		expect(linkTarget('#ch-2', IOS, SITE)).toBeNull();
		expect(linkTarget('/es/sermons/', ANDROID, SITE)).toBeNull();
	});

	it('sends website-only files to the same path on the website', () => {
		expect(linkTarget('/feed.xml', IOS, SITE)).toEqual({ kind: 'external', url: 'https://ochorus.com/feed.xml' });
		expect(linkTarget('/sitemap.xml', ANDROID, SITE)).toEqual({
			kind: 'external',
			url: 'https://ochorus.com/sitemap.xml'
		});
	});

	it('sends a download link (a bundled PDF) to the website', () => {
		expect(linkTarget('/pdfs/humility.pdf', IOS, SITE, { download: true })).toEqual({
			kind: 'external',
			url: 'https://ochorus.com/pdfs/humility.pdf'
		});
	});

	it('opens other origins as they are (the API’s EPUB, a source)', () => {
		const epub = 'https://api.ochorus.com/api/books/humility/epub/?lang=en';
		expect(linkTarget(epub, IOS, SITE, { download: true })).toEqual({ kind: 'external', url: epub });
		expect(linkTarget('https://en.wikipedia.org/wiki/Andrew_Murray', ANDROID, SITE)).toEqual({
			kind: 'external',
			url: 'https://en.wikipedia.org/wiki/Andrew_Murray'
		});
	});

	it('opens an app page asked for in a new tab here (the app has no tabs)', () => {
		expect(linkTarget('/books/humility/', IOS, SITE, { newTab: true })).toEqual({
			kind: 'internal',
			path: '/books/humility/'
		});
		expect(linkTarget('/feed.xml', IOS, SITE, { newTab: true })).toEqual({
			kind: 'external',
			url: 'https://ochorus.com/feed.xml'
		});
	});

	it('keeps an absolute link to the website’s pages inside the app', () => {
		expect(linkTarget('https://ochorus.com/es/books/humility/?x=1#c', IOS, SITE)).toEqual({
			kind: 'internal',
			path: '/es/books/humility/?x=1#c'
		});
		expect(linkTarget('https://ochorus.com/feed.xml', IOS, SITE)).toEqual({
			kind: 'external',
			url: 'https://ochorus.com/feed.xml'
		});
	});

	it('leaves other schemes to the web view (mail, phone, blobs)', () => {
		expect(linkTarget('mailto:support@ochorus.com', IOS, SITE)).toBeNull();
		expect(linkTarget('tel:+256700000000', ANDROID, SITE)).toBeNull();
		expect(linkTarget('blob:capacitor://localhost/abc', IOS, SITE, { download: true })).toBeNull();
		expect(linkTarget('javascript:void(0)', IOS, SITE)).toBeNull();
	});
});
