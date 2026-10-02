import { describe, expect, it } from 'vitest';
import type { BookTile, PlanDay, PlanSummary } from './library-public';
import { relatedPlans, RELATED_PLANS_LIMIT } from './relatedPlans';

const tile = (slug: string, author: string): BookTile => ({
	kind: 'book',
	slug,
	title: slug,
	cover_url: '',
	cover_color: '',
	author: { slug: author, name: author, birth_year: null }
});

const summary = (slug: string, books: [string, string][]): PlanSummary => ({
	slug,
	language: 'en',
	title: slug,
	description: '',
	day_count: 10,
	total_words: 0,
	covers: books.map(([b, a]) => tile(b, a)),
	day_one: null
});

const day = (n: number, book_slug: string): PlanDay => ({
	day: n,
	book_slug,
	chapter_order: n,
	book_title: book_slug,
	chapter_title: '',
	word_count: 0
});

// The current plan reads two Murray books.
const current = {
	slug: 'humility-12-days',
	days: [day(1, 'humility'), day(2, 'humility'), day(3, 'abide-in-christ')],
	authors: [{ slug: 'murray', name: 'Andrew Murray' }],
	covers: [tile('humility', 'murray'), tile('abide-in-christ', 'murray')]
};

describe('relatedPlans', () => {
	it('ranks a shared book above a shared author, and drops plans sharing neither', () => {
		const all = [
			summary('spurgeon-plan', [['all-of-grace', 'spurgeon']]),
			summary('murray-prayer', [['school-of-prayer', 'murray']]), // author only: 1
			summary('deeper-life', [['abide-in-christ', 'murray']]), // book + author: 3
			current as unknown as PlanSummary
		];
		expect(relatedPlans(current, all).map((p) => p.slug)).toEqual(['deeper-life', 'murray-prayer']);
	});

	it('never suggests the plan itself', () => {
		const self = summary('humility-12-days', [['humility', 'murray']]);
		expect(relatedPlans(current, [self])).toEqual([]);
	});

	it('counts every shared book and writer', () => {
		const all = [
			summary('one-book', [['humility', 'murray']]), // 2 + 1 = 3
			summary('two-books', [
				['humility', 'murray'],
				['abide-in-christ', 'murray']
			]), // 4 + 1 = 5
			summary('mixed', [
				['humility', 'murray'],
				['all-of-grace', 'spurgeon']
			]) // 2 + 1 = 3
		];
		expect(relatedPlans(current, all).map((p) => p.slug)).toEqual(['two-books', 'one-book', 'mixed']);
	});

	it('keeps the shelf order on a tie, so the result is deterministic', () => {
		const all = ['c', 'a', 'b'].map((s) => summary(s, [['other', 'murray']]));
		expect(relatedPlans(current, all).map((p) => p.slug)).toEqual(['c', 'a', 'b']);
	});

	it('caps the list', () => {
		const all = Array.from({ length: 8 }, (_, i) => summary(`p${i}`, [['x', 'murray']]));
		expect(relatedPlans(current, all)).toHaveLength(RELATED_PLANS_LIMIT);
		expect(relatedPlans(current, all, 2)).toHaveLength(2);
	});

	it('falls back to the cover strip for writers when the API omits `authors`', () => {
		const old = { ...current, authors: undefined };
		const all = [summary('murray-prayer', [['school-of-prayer', 'murray']])];
		expect(relatedPlans(old, all).map((p) => p.slug)).toEqual(['murray-prayer']);
	});

	it('ignores article days and tiles without an author', () => {
		const withArticle = { ...current, days: [...current.days, { ...day(4, ''), article_slug: 'how-to-pray' }] };
		// An article day's book_slug is '' — it must not match a tile that also lacks one.
		const blank = summary('blank', [['', 'x']]);
		const bare = summary('bare', []);
		bare.covers = [{ ...tile('elsewhere', 'x'), author: undefined }];
		expect(relatedPlans(withArticle, [blank, bare, summary('none', [])])).toEqual([]);
	});

	it('does not treat the house imprint as a shared writer', () => {
		const mixed = {
			...current,
			authors: [...(current.authors ?? []), { slug: 'ochorus-originals', name: 'Ochorus Originals' }]
		};
		const series = summary('rooted-series', [['rooted-1', 'ochorus-originals']]);
		expect(relatedPlans(mixed, [series])).toEqual([]);
	});

	it('returns nothing from an empty list (a failed fetch)', () => {
		expect(relatedPlans(current, [])).toEqual([]);
	});
});
