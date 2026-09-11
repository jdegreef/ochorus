import { describe, expect, it } from 'vitest';

import { countJobsByLanguageType, type AdminTranslationJob } from './library-admin';

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
