import { describe, expect, it } from 'vitest';

import { adminEditionHref, adminEditionId, countJobsByLanguageType, formatDuration, sittingBucketLabel, type AdminTranslationJob } from './library-admin';

describe('adminEditionHref', () => {
	// The audit's "worst books first" Open lands on the edition's section of
	// the admin book page, whose id is adminEditionId.
	it('links to the edition section of the admin book page', () => {
		expect(adminEditionHref('the-key', 'sw')).toBe(`/admin/books/the-key#${adminEditionId('sw')}`);
		expect(adminEditionHref('a b', 'en')).toBe('/admin/books/a%20b#ed-en');
	});
});

// Feeds the dashboard's "+N queued" overlay. The counts come from GitHub-backed
// issues and are grouped client-side, so this guards the grouping against the
// regressions that would otherwise ship silently (CI has no live queue).
describe('countJobsByLanguageType', () => {
	const job = (
		type: AdminTranslationJob['type'],
		language: string,
		state: AdminTranslationJob['state'] = 'queued'
	): AdminTranslationJob => ({
		type,
		language,
		state,
		slug: `${type}-slug`,
		url: '',
		number: 1,
		created_at: ''
	});

	it('counts per language and per type', () => {
		const counts = countJobsByLanguageType([
			job('book', 'es'),
			job('book', 'es'),
			job('article', 'es'),
			job('book', 'sw')
		]);
		expect(counts.es).toEqual({ book: 2, article: 1 });
		expect(counts.sw).toEqual({ book: 1 });
	});

	it('counts in_progress jobs, not just queued (neither is live yet)', () => {
		const counts = countJobsByLanguageType([
			job('book', 'es', 'queued'),
			job('book', 'es', 'in_progress')
		]);
		expect(counts.es?.book).toBe(2);
	});

	it('tallies types with no dashboard column (e.g. topic) without erroring', () => {
		const counts = countJobsByLanguageType([job('topic', 'es'), job('bio', 'es')]);
		// Present in the map but harmless — the table never reads counts.es.topic.
		expect(counts.es).toEqual({ topic: 1, bio: 1 });
	});

	it('returns an empty map for no jobs, so every cell reads 0 (blank, not "+0")', () => {
		const counts = countJobsByLanguageType([]);
		expect(counts).toEqual({});
		expect(counts.es?.book ?? 0).toBe(0);
	});
});

describe('formatDuration', () => {
	it('drops seconds by default, and keeps them under 10 minutes when precise', () => {
		expect(formatDuration(100)).toBe('1m');
		expect(formatDuration(100, { precise: true })).toBe('1m 40s');
		expect(formatDuration(120, { precise: true })).toBe('2m');
		expect(formatDuration(700, { precise: true })).toBe('11m');
		expect(formatDuration(45, { precise: true })).toBe('45s');
		expect(formatDuration(3700, { precise: true })).toBe('1h 1m');
	});
});

describe('sittingBucketLabel', () => {
	it('names a bucket from its bounds', () => {
		expect(sittingBucketLabel({ min_seconds: 0, max_seconds: 60 })).toBe('Under 1m');
		expect(sittingBucketLabel({ min_seconds: 60, max_seconds: 300 })).toBe('1–5m');
		expect(sittingBucketLabel({ min_seconds: 1800, max_seconds: null })).toBe('30m+');
	});
});
