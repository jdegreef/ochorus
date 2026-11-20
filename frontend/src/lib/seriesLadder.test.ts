import { describe, expect, it } from 'vitest';
import { readingLadder } from './seriesLadder';
import type { SeriesSummary } from './library-public';

const s = (slug: string, audience: string, min_age: number | null = null) =>
	({ slug, title: slug, audience, min_age, max_age: null }) as unknown as SeriesSummary;

describe('readingLadder', () => {
	it('climbs by lowest age, teens without one on the teens floor, adults on top', () => {
		const rungs = readingLadder([
			s('bible', 'adults'),
			s('rooted', 'young_readers', 9),
			s('tell', 'young_readers', 6),
			s('talk', 'teens'),
			s('anchored', 'teens', 13),
			s('brave', 'young_readers', 8),
			s('kt', 'adults'),
			s('poc', 'adults'),
			s('extra', 'adults')
		]);
		expect(rungs.map((r) => [r.min, r.series.map((x) => x.slug)])).toEqual([
			[6, ['tell']],
			[8, ['brave']],
			[9, ['rooted']],
			[13, ['talk', 'anchored']],
			[null, ['bible', 'kt', 'poc']]
		]);
	});
});
