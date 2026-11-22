import { afterEach, describe, expect, it } from 'vitest';
import { getLocale, overwriteGetLocale } from '$lib/paraglide/runtime';
import { i18n, loadUiCatalog } from './i18n.svelte';

/**
 * Counts in languages with more than one/many forms. A one/many pair made
 * the Arabic Books page say "81 كتب" (11–99 take the singular accusative,
 * كتابًا) and Russian "2 книг" (2–4 take книги).
 */
const original = getLocale;
const as = async (locale: string) => {
	await loadUiCatalog(locale);
	overwriteGetLocale(() => locale as ReturnType<typeof getLocale>);
};
const book = (n: number) => i18n.tn(n, 'common.bookOne', 'common.bookMany');

afterEach(() => overwriteGetLocale(original));

describe('tn', () => {
	it('keeps English to its one/many pair', async () => {
		await as('en');
		expect([book(1), book(2), book(81)]).toEqual(['book', 'books', 'books']);
	});

	it('gives Arabic its dual, few, many and other forms', async () => {
		await as('ar');
		expect([book(1), book(2), book(5), book(81), book(100)]).toEqual([
			'كتاب',
			'كتابان',
			'كتب',
			'كتابًا',
			'كتاب'
		]);
	});

	it('gives Russian and Ukrainian one, few and many — 21 is singular', async () => {
		await as('ru');
		expect([book(1), book(3), book(5), book(21), book(24)]).toEqual([
			'книга',
			'книги',
			'книг',
			'книга',
			'книги'
		]);
		await as('uk');
		expect([i18n.tn(12, 'common.authorOne', 'common.authorMany')]).toEqual(['авторів']);
	});

	it('falls back to the pair for a noun with no forms file entry', async () => {
		await as('ru');
		expect(i18n.tn(5, 'quotes.worksOne', 'quotes.worksMany')).toBe(i18n.t('quotes.worksMany'));
	});
});
