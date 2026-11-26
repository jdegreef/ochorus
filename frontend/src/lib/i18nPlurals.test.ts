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

/**
 * Number and noun in the locale's order. Swahili and Luganda count noun-first
 * ("vitabu 66", "ebitabo 66"); the site used to glue every count number-first
 * and print "66 vitabu · 1,189 sura" on /sw/bible/.
 */
describe('count', () => {
	const books = (n: number, shown?: string) => i18n.count(n, 'common.bookOne', 'common.bookMany', shown);
	const chapters = (n: number, shown?: string) =>
		i18n.count(n, 'book.chapterOne', 'book.chaptersMany', shown);

	it('puts the Swahili number after its noun', async () => {
		await as('sw');
		expect(`${books(66)} · ${chapters(1189, '1,189')}`).toBe('vitabu 66 · sura 1,189');
		expect(books(1)).toBe('kitabu 1');
		expect(i18n.count(3, 'common.seriesOne', 'common.seriesMany')).toBe('mifululizo 3 ya vitabu');
		expect(i18n.unit('common.min', 5)).toBe('dakika 5');
		expect(i18n.unit('plans.days', '3 kati ya 30')).toBe('siku 3 kati ya 30');
	});

	it('and the Luganda one', async () => {
		await as('lg');
		expect(books(66)).toBe('ebitabo 66');
		expect(i18n.unit('plans.days', 30)).toBe('ennaku 30');
	});

	it('keeps number-first locales as they were', async () => {
		await as('en');
		expect([books(1), books(66), chapters(1189, '1,189')]).toEqual(['1 book', '66 books', '1,189 chapters']);
		expect(i18n.unit('plans.days', '3 of 30')).toBe('3 of 30 days');
		await as('ru');
		expect(books(5)).toBe('5 книг');
		await as('ar');
		expect(books(81)).toBe('81 كتابًا');
	});
});

describe('no count is glued number-first in code', () => {
	it('every number + noun goes through i18n.count / i18n.unit', () => {
		// `${n} ${i18n.tn(…)}` or `{n} {i18n.tn(…)}` hard-codes English word order.
		const glued = /(\$\{[^{}]+\} \$\{|\{[^{}#/:@]+\}\s+\{)i18n\.tn\(/;
		const offenders = Object.entries(
			import.meta.glob<string>(['/src/**/*.svelte', '/src/**/*.ts', '!/src/**/*.test.ts', '!/src/lib/paraglide/**'], {
				query: '?raw',
				import: 'default',
				eager: true
			})
		)
			.filter(([, src]) => glued.test(src))
			.map(([path]) => path);
		expect(offenders).toEqual([]);
	});

	it('a noun that places its own number (%n%) is only read through count / unit', async () => {
		// "vitabu %n%" read with t() or a bare tn() would print a literal %n%.
		const { readFileSync } = await import('node:fs');
		const cat = (l: string) => JSON.parse(readFileSync(`messages/${l}.json`, 'utf8')) as Record<string, string>;
		const en = cat('en');
		const placed = new Set(
			['sw', 'lg'].flatMap((l) => Object.entries(cat(l)))
				.filter(([k, v]) => v.includes('%n%') && !en[k]?.includes('%n%'))
				.map(([k]) => k)
		);
		const snake = (key: string) => key.replace(/([a-z0-9])([A-Z])/g, '$1_$2').replace(/\./g, '_').toLowerCase();
		const sources = import.meta.glob<string>(
			['/src/**/*.svelte', '/src/**/*.ts', '!/src/**/*.test.ts', '!/src/lib/paraglide/**', '!/src/lib/i18n.svelte.ts'],
			{ query: '?raw', import: 'default', eager: true }
		);
		// count / unit, or a durationLabel key (reading.ts places %n% itself).
		const ok = /(?:\bmin:\s*|\b(?:count|unit)\(\s*(?:[^,()]+(?:\([^()]*\))?,\s*)?(?:'[a-zA-Z0-9_.]+',\s*)?)$/;
		const offenders: string[] = [];
		for (const [path, src] of Object.entries(sources)) {
			for (const m of src.matchAll(/'([a-zA-Z0-9_]+\.[a-zA-Z0-9_.]+)'/g)) {
				if (!placed.has(snake(m[1]))) continue;
				if (!ok.test(src.slice(Math.max(0, m.index! - 200), m.index))) offenders.push(`${path}: ${m[1]}`);
			}
		}
		expect(placed.size).toBeGreaterThan(30);
		expect(offenders).toEqual([]);
	});
});
