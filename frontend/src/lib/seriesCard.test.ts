import { describe, expect, it } from 'vitest';
import { seriesCardUrl } from './seriesCard';

describe('series share card', () => {
	it('lives at one path per series per language', () => {
		expect(seriesCardUrl('rooted', 'ar')).toBe('/og/series/ar/rooted.jpg');
	});
});
