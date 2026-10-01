import { describe, expect, it } from 'vitest';
import { healthBand, nextActions, pointsBreakdown, type HealthWeights } from './languageHealth';
import type { AdminLanguageHealth } from './library-admin';

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
			readiness: { ready: false, blocking: ['glossary', 'ui'] }
		});
		const [top] = nextActions(l, 179, WEIGHTS, (k) => ({ glossary: 'Glossary', ui: 'Interface' })[k] ?? k);
		expect(top.key).toBe('readiness');
		expect(top.label).toBe('Clear the go-live blockers: Glossary, Interface');
		expect(top.href).toBe('/admin/languages/fr#sec-readiness');
	});

	it('has nothing to say about the source language', () => {
		expect(nextActions(french({ is_source: true }), 179, WEIGHTS)).toEqual([]);
	});
});
