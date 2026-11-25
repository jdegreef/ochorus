import { describe, expect, it } from 'vitest';
import {
	CATALOG,
	catalogPath,
	countLabel,
	queryFromUrl,
	urlSearch,
	type CatalogRow
} from './adminCatalog';
import { ADMIN_SECTIONS } from './adminSections';

const row = (extra: Partial<CatalogRow> = {}): CatalogRow => ({
	slug: 'humility',
	title: 'Humility',
	...extra
});

describe('catalogPath', () => {
	it('leaves empty filters and page 1 off', () => {
		expect(catalogPath('books', {})).toBe('/api/admin/catalog/books/');
		expect(catalogPath('books', { q: '', page: 1, language: 'es' })).toBe(
			'/api/admin/catalog/books/?language=es'
		);
		expect(catalogPath('quotes', { q: 'a b', page: 3 })).toBe(
			'/api/admin/catalog/quotes/?q=a+b&page=3'
		);
	});
});

describe('queryFromUrl / urlSearch', () => {
	it('round-trips a filtered list through its URL', () => {
		const q = queryFromUrl(new URLSearchParams('q=murray&status=unpublished&page=2'));
		expect(q).toMatchObject({ q: 'murray', status: 'unpublished', page: 2, language: '' });
		expect(urlSearch(q)).toBe('?q=murray&status=unpublished&page=2');
	});

	it('treats a junk or first page as page 1', () => {
		expect(queryFromUrl(new URLSearchParams('page=abc')).page).toBe(1);
		expect(queryFromUrl(new URLSearchParams('page=-4')).page).toBe(1);
		expect(urlSearch(queryFromUrl(new URLSearchParams('')))).toBe('');
	});
});

describe('countLabel', () => {
	it('pluralises, except a noun that already ends in s', () => {
		expect(countLabel(1, 'book')).toBe('1 book');
		expect(countLabel(1200, 'book')).toBe('1,200 books');
		expect(countLabel(2, 'series')).toBe('2 series');
	});
});

describe('CATALOG', () => {
	it('links books and sermons to their admin pages, and every kind to the site', () => {
		expect(CATALOG.books.adminHref!(row())).toBe('/admin/books/humility');
		expect(CATALOG.sermons.adminHref!(row({ slug: 'do-you-pray' }))).toBe(
			'/admin/sermons/do-you-pray'
		);
		expect(CATALOG.authors.adminHref).toBeUndefined();
		expect(CATALOG.quotes.siteHref(row({ author: { slug: 'am', name: 'A' } }))).toBe('/quotes/am');
		expect(CATALOG.topics.siteHref(row({ slug: 'prayer' }))).toBe('/topics/prayer');
	});

	it('says what an author is missing, but never of an imprint', () => {
		expect(CATALOG.authors.meta(row({ years: '1828–1917', has_bio: false, has_photo: true }))).toBe(
			'1828–1917 · no biography'
		);
		expect(CATALOG.authors.meta(row({ is_imprint: true, has_bio: false, has_photo: false }))).toBe(
			'imprint'
		);
	});

	it('has a rail entry for every list', () => {
		const hrefs = ADMIN_SECTIONS.map((s) => s.href);
		for (const kind of Object.keys(CATALOG)) expect(hrefs).toContain(`/admin/${kind}`);
	});
});
