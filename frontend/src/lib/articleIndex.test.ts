import { describe, expect, it } from 'vitest';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import type { ArticleSummary, CoverBook } from './library-public';
import {
	FEATURED_ARTICLES,
	featuredArticles,
	isGuide,
	matchesQuery,
	ofKind,
	sortArticles,
	topicGroups
} from './articleIndex';

const book = (title: string, author: string): CoverBook =>
	({ slug: title.toLowerCase(), title, author: { slug: 'a', name: author, birth_year: null } }) as unknown as CoverBook;

function art(slug: string, over: Partial<ArticleSummary> = {}): ArticleSummary {
	return {
		slug,
		language: 'en',
		h1: slug,
		meta_title: '',
		description: '',
		source_type: 'public_domain',
		word_count: 1000,
		sort_order: 0,
		created_at: '2026-09-01T00:00:00Z',
		topics: [],
		...over
	};
}

describe('isGuide / ofKind', () => {
	it('reads the API kind, falling back to the -guide slug convention', () => {
		expect(isGuide(art('x', { kind: 'guide' }))).toBe(true);
		expect(isGuide(art('humility-guide', { kind: 'article' }))).toBe(false);
		expect(isGuide(art('humility-guide'))).toBe(true);
		expect(isGuide(art('how-to-pray'))).toBe(false);
	});

	it('filters by the Questions / Book guides switch; "" keeps everything', () => {
		const g = art('a-guide');
		const q = art('how-to-pray');
		expect([g, q].filter((a) => ofKind(a, 'guides'))).toEqual([g]);
		expect([g, q].filter((a) => ofKind(a, 'questions'))).toEqual([q]);
		expect([g, q].filter((a) => ofKind(a, ''))).toEqual([g, q]);
	});
});

describe('matchesQuery', () => {
	const a = art('how-to-pray-so-god-answers', {
		h1: 'How to Pray So That God Answers',
		description: 'Lessons from George Müller.',
		lead_book: book('The Life of Trust', 'George Müller'),
		topics: [{ slug: 'prayer', title: 'Prayer' }]
	});

	it('matches the headline, standfirst, lead book, its author and topics, case-insensitively', () => {
		for (const q of ['pray so', 'MÜLLER', 'life of trust', 'prayer', '  answers  ']) {
			expect(matchesQuery(a, q), q).toBe(true);
		}
		expect(matchesQuery(a, 'spurgeon')).toBe(false);
	});

	it('an empty query matches everything, and a missing lead book is fine', () => {
		expect(matchesQuery(art('x'), '')).toBe(true);
		expect(matchesQuery(art('x', { lead_book: null }), 'trust')).toBe(false);
	});
});

describe('sortArticles', () => {
	const a = art('a', { h1: 'Beta', word_count: 900, created_at: '2026-08-01T00:00:00Z' });
	const b = art('b', { h1: 'Alpha', word_count: 300, created_at: '2026-09-20T00:00:00Z' });
	const c = art('c', { h1: 'Gamma', word_count: 2000, created_at: '2026-09-01T00:00:00Z' });
	const shelf = [a, b, c];
	const slugs = (xs: ArticleSummary[]) => xs.map((x) => x.slug);

	it('featured keeps the curated (API) order without copying', () => {
		expect(sortArticles(shelf, 'featured')).toBe(shelf);
	});
	it('orders newest, shortest and A–Z without mutating the shelf', () => {
		expect(slugs(sortArticles(shelf, 'newest'))).toEqual(['b', 'c', 'a']);
		expect(slugs(sortArticles(shelf, 'shortest'))).toEqual(['b', 'a', 'c']);
		expect(slugs(sortArticles(shelf, 'title'))).toEqual(['b', 'a', 'c']);
		expect(slugs(shelf)).toEqual(['a', 'b', 'c']);
	});
});

describe('featuredArticles', () => {
	it('takes the editorial picks in order, skipping missing ones', () => {
		const shelf = [art('z'), art(FEATURED_ARTICLES[2]), art(FEATURED_ARTICLES[0])];
		expect(featuredArticles(shelf).map((a) => a.slug)).toEqual([
			FEATURED_ARTICLES[0],
			FEATURED_ARTICLES[2],
			'z'
		]);
	});

	it('fills a gap from the curated order with questions, never guides', () => {
		const shelf = [art('one-guide'), art('q1'), art('q2'), art('q3')];
		expect(featuredArticles(shelf).map((a) => a.slug)).toEqual(['q1', 'q2', 'q3']);
	});

	it('names articles that exist in the English fixture', () => {
		// The picks are editorial slugs; a rename would otherwise silently fall
		// back to the curated order and nobody would notice.
		const dir = resolve(import.meta.dirname, '../../../backend/library/fixtures/content/articles');
		for (const slug of FEATURED_ARTICLES) {
			expect(existsSync(resolve(dir, `${slug}.en.json`)), slug).toBe(true);
		}
	});
});

describe('topicGroups', () => {
	const prayer = { slug: 'prayer', title: 'Prayer' };
	const grace = { slug: 'grace', title: 'Grace' };
	const faith = { slug: 'faith', title: 'Faith' };
	const shelf = [
		art('p1', { topics: [prayer] }),
		art('p2', { topics: [prayer, grace] }),
		art('p-guide', { topics: [prayer] }),
		art('p3', { topics: [prayer] }),
		art('p4', { topics: [prayer] }),
		art('g1', { topics: [grace] }),
		art('f1', { topics: [faith] }),
		art('only-guide', { topics: [{ slug: 'classics', title: 'Classics' }] })
	];

	it('orders topics by size then title, previewing the first questions only', () => {
		const groups = topicGroups(shelf, 6, 3);
		expect(groups.map((g) => [g.slug, g.count])).toEqual([
			['prayer', 5],
			['grace', 2],
			['faith', 1]
		]);
		// The guide is counted but not previewed; the preview stops at three.
		expect(groups[0].items.map((a) => a.slug)).toEqual(['p1', 'p2', 'p3']);
	});

	it('drops a topic with nothing to preview and honours the limit', () => {
		expect(topicGroups(shelf).some((g) => g.slug === 'classics')).toBe(false);
		expect(topicGroups(shelf, 2).map((g) => g.slug)).toEqual(['prayer', 'grace']);
	});
});
