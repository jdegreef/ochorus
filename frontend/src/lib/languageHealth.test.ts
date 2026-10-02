import { describe, expect, it } from 'vitest';
import {
	blockers,
	checkLabels,
	countLine,
	healthBand,
	nextActions,
	plural,
	pointsBreakdown,
	portfolio,
	sparkPoints,
	weekTrend,
	type CoverageShelf
} from './languageHealth';
import type { AdminLanguageHealth, HealthWeights } from './library-admin';

const WEIGHTS: HealthWeights = { readiness: 0.35, coverage: 0.3, review: 0.2, engagement: 0.15 };

// French as the live scoreboard showed it: 53 of 179 books, 50 unreviewed, 5 readers.
const french = (over: Partial<AdminLanguageHealth> = {}): AdminLanguageHealth => ({
	code: 'fr',
	name: 'French',
	native_name: 'Français',
	rtl: false,
	is_source: false,
	is_live: true,
	health: 49,
	scores: { readiness: 1, coverage: 0.296, review: 0.057, engagement: 0.238 },
	content: { published_books: 53, unreviewed_books: 50, sermons: 57, bios: 61, plans: 11, chapters: 0, words: 0 },
	readiness: { ready: true, blocking: [] },
	readers: 5,
	reading_elsewhere: 0,
	...over
});

describe('pointsBreakdown', () => {
	it('splits 100 points by weight and composes the score', () => {
		const pts = pointsBreakdown(french().scores, WEIGHTS);
		expect(pts.map((p) => p.max)).toEqual([35, 30, 20, 15]);
		const earned = pts.reduce((s, p) => s + p.earned, 0);
		expect(Math.round(earned)).toBe(49);
		for (const p of pts) expect(p.earned + p.lost).toBeCloseTo(p.max);
	});

	it('clamps out-of-range scores', () => {
		const pts = pointsBreakdown({ readiness: 1.2, coverage: -0.1, review: 0, engagement: 0 }, WEIGHTS);
		expect(pts[0].earned).toBe(35);
		expect(pts[1].earned).toBe(0);
	});
});

describe('healthBand', () => {
	it('names the band at its edges', () => {
		expect(healthBand(75).label).toBe('Strong');
		expect(healthBand(74).label).toBe('Fair');
		expect(healthBand(45).label).toBe('Fair');
		expect(healthBand(44).label).toBe('Weak');
	});
});

describe('nextActions', () => {
	it('leads with the biggest actionable gain and prices one book', () => {
		const [top, then] = nextActions(french(), 179, WEIGHTS);
		expect(top.key).toBe('coverage');
		expect(top.gain).toBeCloseTo(21.1, 1);
		expect(top.perUnit).toBeCloseTo(30 / 179);
		expect(then.key).toBe('review');
		expect(then.href).toBe('/admin/review?language=fr');
		expect(then.label).toBe('Review 50 AI-translated books');
		expect(then.perUnit).toBeCloseTo(20 / 53);
	});

	it('never recommends engagement, and drops maxed levers', () => {
		const acts = nextActions(french(), 179, WEIGHTS);
		expect(acts.map((a) => a.key)).not.toContain('engagement');
		expect(acts.map((a) => a.key)).not.toContain('readiness');
	});

	it('names the blocking checks when readiness leads', () => {
		const l = french({
			scores: { readiness: 0.5, coverage: 0.9, review: 1, engagement: 0 },
			content: { ...french().content, unreviewed_books: 0 },
			readiness: {
				ready: false,
				blocking: [
					{ key: 'glossary', label: 'Glossary' },
					{ key: 'ui', label: 'Interface strings' }
				]
			}
		});
		const [top] = nextActions(l, 179, WEIGHTS);
		expect(top.key).toBe('readiness');
		expect(top.label).toBe('Clear the go-live blockers: Glossary, Interface strings');
		expect(top.href).toBe('/admin/languages/fr#sec-readiness');
	});

	it('has nothing to say about the source language', () => {
		expect(nextActions(french({ is_source: true }), 179, WEIGHTS)).toEqual([]);
	});
});

describe('plural', () => {
	it('formats the count', () => {
		expect(plural(1, 'reader')).toBe('1 reader');
		expect(plural(12345, 'reader')).toBe('12,345 readers');
	});
});

describe('blockers', () => {
	it('reads a bare key from an older API as its own label', () => {
		const l = french({ readiness: { ready: false, blocking: ['ui'] as never } });
		expect(blockers(l)).toEqual([{ key: 'ui', label: 'ui' }]);
	});
});

describe('countLine', () => {
	it('shows readers against the engagement target', () => {
		expect(countLine('engagement', french(), 179, 25)).toBe('5 of 25 readers');
	});

	it('says the target is met rather than "30 of 25"', () => {
		expect(countLine('engagement', french({ readers: 30 }), 179, 25)).toBe('target met (30 readers)');
	});

	it('falls back to the bare count from an API without a target', () => {
		expect(countLine('engagement', french(), 179)).toBe('5 readers');
	});

	it('gives the counts behind coverage and review', () => {
		expect(countLine('coverage', french(), 179)).toBe('53 of 179 books');
		expect(countLine('review', french(), 179)).toBe('3 of 53 reviewed');
	});
});

// English's shelf from the screenshot, under the recommended mix.
const SHELF: CoverageShelf = {
	mix: { books: 0.5, sermons: 0.25, bios: 0.15, plans: 0.1 },
	source: { books: 179, sermons: 198, bios: 99, plans: 36 }
};

describe('coverage across content kinds', () => {
	it('shows each kind as a share of the source shelf', () => {
		expect(countLine('coverage', french(), 179, 25, SHELF)).toBe(
			'books 30% · sermons 29% · bios 62% · plans 31%'
		);
	});

	it('names what is missing and prices one book at its share of the mix', () => {
		const l = french({ scores: { ...french().scores, coverage: 0.343 } });
		const cov = nextActions(l, 179, WEIGHTS, SHELF).find((a) => a.key === 'coverage')!;
		expect(cov.label).toBe('Translate the missing content (126 books, 141 sermons, 38 bios, 25 plans)');
		expect(cov.perUnit).toBeCloseTo((30 * 0.5) / 179);
		// Books cost the most points, so the button opens them.
		expect(cov.href).toBe('/admin/languages/fr#sec-books');
	});

	it('uses the singular for one missing item, and points at the costliest gap', () => {
		const l = french({
			content: { ...french().content, published_books: 179, sermons: 197, bios: 60, plans: 35 },
			scores: { ...french().scores, coverage: 0.93 }
		});
		const cov = nextActions(l, 179, WEIGHTS, SHELF).find((a) => a.key === 'coverage')!;
		expect(cov.label).toBe('Translate the missing content (1 sermon, 39 bios, 1 plan)');
		expect(cov.href).toBe('/admin/languages/fr#sec-bios');
		// Every book is here, so another book is worth nothing.
		expect(cov.perUnit).toBeNull();
	});

	it('says so when there is no English shelf to compare against', () => {
		const empty = { ...SHELF, source: { books: 0, sermons: 0, bios: 0, plans: 0 } };
		expect(countLine('coverage', french(), 0, 25, empty)).toBe('no English shelf to compare');
	});

	it('leaves out a kind the source shelf has none of', () => {
		const noPlans = { ...SHELF, source: { ...SHELF.source, plans: 0 } };
		expect(countLine('coverage', french(), 179, 25, noPlans)).toBe('books 30% · sermons 29% · bios 62%');
		const cov = nextActions(french(), 179, WEIGHTS, noPlans).find((a) => a.key === 'coverage')!;
		expect(cov.perUnit).toBeCloseTo((30 * 0.5) / 0.9 / 179);
	});
});

describe('checkLabels', () => {
	const check = (key: string, label: string) => ({
		key,
		label,
		status: 'fail' as const,
		detail: '',
		current: null,
		required: null
	});

	it("names each blocking check by its report's own label", () => {
		const r = {
			blocking: ['ui', 'bios'],
			checks: [check('ui', 'Interface strings'), check('bios', 'Biographies'), check('books', 'Books')]
		};
		expect(checkLabels(r, r.blocking)).toEqual(['Interface strings', 'Biographies']);
	});

	it('falls back to the key for a check the report does not list', () => {
		expect(checkLabels({ checks: [] }, ['new-check'])).toEqual(['new-check']);
	});
});

describe('weekTrend', () => {
	it('is no chip until a week-old point exists', () => {
		expect(weekTrend(null)).toBeNull();
		expect(weekTrend(undefined)).toBeNull();
	});

	it('reads the change in points', () => {
		expect(weekTrend(4)).toEqual({ dir: 'up', text: '4 this week' });
		expect(weekTrend(-2)).toEqual({ dir: 'down', text: '2 this week' });
		expect(weekTrend(0)).toEqual({ dir: 'flat', text: 'no change this week' });
	});
});

describe('sparkPoints', () => {
	it('needs two points', () => {
		expect(sparkPoints(undefined)).toBe('');
		expect(sparkPoints([{ date: '2026-10-02', health: 49 }])).toBe('');
	});

	it('places points by date and fills the box with their range', () => {
		const pts = sparkPoints([
			{ date: '2026-10-01', health: 40 },
			{ date: '2026-10-02', health: 50 },
			{ date: '2026-10-05', health: 60 }
		]);
		// Day 1 of a 4-day span sits a quarter of the way along.
		expect(pts).toBe('0,26 25,14 100,2');
	});

	it('keeps a small change small by spanning at least ten points', () => {
		// 49 → 50 sits in the middle of a 44.5–54.5 band, not top to bottom.
		expect(sparkPoints([
			{ date: '2026-10-01', health: 49 },
			{ date: '2026-10-02', health: 50 }
		])).toBe('0,15.2 100,12.8');
	});
});

describe('portfolio', () => {
	const en = french({ code: 'en', is_source: true, health: 98, content: { ...french().content, unreviewed_books: 1 } });
	const sw = french({ code: 'sw', health: 52, content: { ...french().content, unreviewed_books: 65 } });
	const uk = french({
		code: 'uk',
		health: 27,
		is_live: false,
		content: { ...french().content, unreviewed_books: 0 },
		readiness: { ready: false, blocking: [{ key: 'glossary', label: 'Glossary' }] }
	});

	it('summarises the translations, leaving the source out of the score figures', () => {
		const p = portfolio([en, french(), sw, uk]);
		expect(p.translations).toBe(3);
		expect(p.live).toBe(2);
		expect(p.median).toBe(49);
		expect(p.awaitingReview).toBe(1 + 50 + 65);
		expect(p.blocked.map((l) => l.code)).toEqual(['uk']);
	});

	it('averages the middle pair for an even count, and has no median when empty', () => {
		expect(portfolio([french(), sw]).median).toBe(51);
		expect(portfolio([en]).median).toBeNull();
	});
});
