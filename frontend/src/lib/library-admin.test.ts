import { describe, expect, it } from 'vitest';

import { countJobsByLanguageType, periodTrend, type AdminTranslationJob } from './library-admin';

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

describe('periodTrend', () => {
	it('shows a change on a small base as a count, with the old figure in the tooltip', () => {
		expect(periodTrend(25, 2)).toEqual({ dir: 'up', text: '+23', title: 'Was 2 in the previous period' });
		expect(periodTrend(3, 8)).toEqual({ dir: 'down', text: '-5', title: 'Was 8 in the previous period' });
		expect(periodTrend(4, 4)).toEqual({ dir: 'flat', text: '0', title: 'Was 4 in the previous period' });
	});

	it('switches to a percentage once the base is big enough to mean something', () => {
		expect(periodTrend(15, 10)).toEqual({ dir: 'up', text: '+50%' });
		expect(periodTrend(10, 10)).toEqual({ dir: 'flat', text: '0%' });
	});

	it('reads a metric with no baseline as new, and nothing at all as nothing', () => {
		expect(periodTrend(3, 0)).toEqual({ dir: 'up', text: 'new' });
		expect(periodTrend(0, 0)).toBeNull();
	});
});
