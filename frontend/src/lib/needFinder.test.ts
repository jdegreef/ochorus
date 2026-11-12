import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import en from '../../messages/en.json';
import type { BookSummary, PlanSummary, SermonSummary, TopicDetail } from './library-public';
import { TOPIC_GROUPS } from './topicGroups';
import {
	NEEDS,
	NEED_MIN_CHIPS,
	SHORT_READ_WORDS,
	availableNeeds,
	choosePicks,
	needLabelKey,
	type Need
} from './needFinder';

const BACKEND = join(process.cwd(), '..', 'backend', 'library');

/** The first string of each `("slug", "Title",` tuple in a seed module — the
 *  reader topicGroups.test.ts uses for topics, applied to plans too. */
const seedSlugs = (file: string): Set<string> =>
	new Set(
		[...readFileSync(join(BACKEND, file), 'utf-8').matchAll(/\(\s*"([a-z0-9-]+)",\s*\n\s*"[^"]+",/g)].map(
			(m) => m[1]
		)
	);

const snake = (key: string) =>
	key
		.replace(/([a-z0-9])([A-Z])/g, '$1_$2')
		.replace(/\./g, '_')
		.toLowerCase();

describe('the situation map', () => {
	it('points every situation at a seeded topic placed in a family', () => {
		const topics = seedSlugs('topic_seed.py');
		const grouped = new Set<string>(TOPIC_GROUPS.flatMap((g) => [...g.slugs]));
		expect(NEEDS.filter((n) => !topics.has(n.topic) || !grouped.has(n.topic))).toEqual([]);
	});

	it('points every plan at a seeded reading plan', () => {
		const plans = seedSlugs('plan_seed.py');
		expect(NEEDS.filter((n) => n.plan && !plans.has(n.plan))).toEqual([]);
	});

	it('has 6–8 distinct situations on distinct shelves, each labelled in the catalogue', () => {
		expect(NEEDS.length).toBeGreaterThanOrEqual(6);
		expect(NEEDS.length).toBeLessThanOrEqual(8);
		expect(new Set(NEEDS.map((n) => n.id)).size).toBe(NEEDS.length);
		expect(new Set(NEEDS.map((n) => n.topic)).size).toBe(NEEDS.length);
		const keys = [
			'home.need.title',
			'home.need.more',
			...NEEDS.map((n) => needLabelKey(n.id)),
			...['shortRead', 'book', 'plan', 'article', 'life'].map((k) => `home.need.${k}`)
		];
		expect(keys.filter((k) => !(snake(k) in en))).toEqual([]);
	});
});

const count = (slug: string, book_count: number, sermon_count: number) => ({ slug, book_count, sermon_count });

describe('availableNeeds — language gating', () => {
	it('keeps the situations whose shelf has three works, a book among them, in NEEDS order', () => {
		const topics = [
			count('deeper-life', 5, 2),
			count('prayer', 1, 2),
			count('grace-and-comfort', 3, 0),
			count('faith-and-guidance', 0, 9), // sermons only: no book to offer
			count('the-gospel-call', 1, 1) // two works
		];
		expect(availableNeeds(topics)).toEqual(['prayerDry', 'grieving', 'deeper']);
	});

	it(`hides the finder below ${NEED_MIN_CHIPS} situations`, () => {
		expect(availableNeeds([count('prayer', 4, 4), count('deeper-life', 4, 4)])).toEqual([]);
		expect(availableNeeds([])).toEqual([]);
	});

	it('shows every situation in a language that has every shelf', () => {
		expect(availableNeeds(NEEDS.map((n) => count(n.topic, 10, 10)))).toEqual(NEEDS.map((n) => n.id));
	});
});

const author = (slug: string) => ({ slug, name: slug.toUpperCase(), photo_url: '' });
const book = (slug: string, authorSlug: string, words = 50000, chapters = 10) =>
	({
		slug,
		language: 'en',
		title: `Book ${slug}`,
		author: author(authorSlug),
		cover_url: '',
		cover_color: '#000',
		word_count: words,
		chapter_count: chapters
	}) as unknown as BookSummary;
const sermon = (slug: string, words: number) =>
	({ slug, language: 'en', title: `Sermon ${slug}`, word_count: words, author: author('spurgeon') }) as unknown as SermonSummary;
const topic = (parts: Partial<TopicDetail>): TopicDetail =>
	({
		slug: 'prayer',
		title: 'On Prayer',
		books: [],
		sermons: [],
		articles: [],
		authors: [],
		...parts
	}) as TopicDetail;
const plan = (slug: string) => ({ slug, language: 'en', title: `Plan ${slug}`, covers: [] }) as unknown as PlanSummary;
const NEED: Need = { id: 'prayerDry', topic: 'prayer', plan: 'school-of-prayer' };

describe('choosePicks — pick selection', () => {
	it('picks the first short sermon, the lead book and the situation’s plan', () => {
		const { picks, topic: t } = choosePicks(
			NEED,
			topic({
				books: [book('the-inner-chamber', 'murray'), book('prevailing-prayer', 'moody')],
				sermons: [sermon('long', SHORT_READ_WORDS + 1), sermon('short', 3000), sermon('shorter', 2000)]
			}),
			[plan('other'), plan('school-of-prayer')]
		);
		expect(t).toEqual({ slug: 'prayer', title: 'On Prayer' });
		expect(picks.map((p) => [p.kind, p.href])).toEqual([
			['shortRead', '/sermons/short'],
			['book', '/books/the-inner-chamber'],
			['plan', '/plans/school-of-prayer']
		]);
	});

	it('falls back to the shortest sermon when none is short', () => {
		const { picks } = choosePicks(
			NEED,
			topic({ books: [book('a', 'x')], sermons: [sermon('long', 9000), sermon('less-long', 7000)] }),
			[]
		);
		expect(picks[0].href).toBe('/sermons/less-long');
	});

	it('without sermons, offers chapter one of the book with the shortest chapters — not the lead', () => {
		const { picks } = choosePicks(
			NEED,
			topic({
				books: [book('lead', 'x', 10000, 100), book('long-chapters', 'y', 90000, 3), book('short-chapters', 'z', 20000, 10)]
			}),
			[]
		);
		expect(picks.slice(0, 2).map((p) => p.href)).toEqual(['/books/short-chapters/1', '/books/lead']);
		expect(picks[0].chapter).toBe(1);
	});

	it('leads with a full text over a young-reader edition', () => {
		const { picks } = choosePicks(
			NEED,
			topic({ books: [book('lead-teens', 'x'), book('lead', 'x')], sermons: [sermon('s', 1000)] }),
			[]
		);
		expect(picks[1].href).toBe('/books/lead');
	});

	it('without the plan in this language, offers an article, then a life by another author', () => {
		const base = { books: [book('lead', 'murray')], sermons: [sermon('s', 1000)] };
		const article = { slug: 'why-pray', h1: 'Why pray?', word_count: 1800, language: 'en', lead_book: null };
		const withArticle = choosePicks(NEED, topic({ ...base, articles: [article] as unknown as TopicDetail['articles'] }), [
			plan('something-else')
		]);
		expect(withArticle.picks[2]).toMatchObject({ kind: 'article', href: '/articles/why-pray/', title: 'Why pray?' });

		const authors = [
			{ ...author('murray'), birth_year: 1828, death_year: 1917 },
			{ ...author('bounds'), birth_year: 1835, death_year: 1913 }
		];
		const withLife = choosePicks(NEED, topic({ ...base, authors }), []);
		expect(withLife.picks[2]).toMatchObject({ kind: 'life', href: '/authors/bounds', byline: '1835–1913' });
	});

	it('shows what a thinner-than-promised shelf has, never a pick twice', () => {
		const { picks } = choosePicks(NEED, topic({ books: [book('only', 'x')] }), []);
		expect(picks.map((p) => p.href)).toEqual(['/books/only']);
	});
});
