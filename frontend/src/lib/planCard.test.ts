import { describe, it, expect } from 'vitest';
import { minutesPerDay, planCardUrl, planData } from './planCard';

const inlined = (url: string, body: unknown, status = 200) =>
	`<script type="application/json" data-sveltekit-fetched data-url="${url}" data-hash="1">` +
	JSON.stringify({ status, statusText: '', headers: {}, body: JSON.stringify(body) }) +
	'</script>';

const API = 'https://api.ochorus.com/api/library/plans';

describe('plan share card', () => {
	it('lives at one path per plan per language', () => {
		expect(planCardUrl('school-of-prayer', 'ar')).toBe('/og/plans/ar/school-of-prayer.jpg');
	});

	it('reads the plan a page was rendered from, past an inlined 404', () => {
		const plan = { slug: 'humility-12-days', title: 'Humility in 12 Days' };
		const html =
			inlined(`${API}/humility-12-days/?language=lg`, { detail: 'Not found.' }, 404) +
			inlined(`${API}/humility-12-days/?language=en`, plan);
		expect(planData(html)).toEqual({ plan, language: 'en' });
		expect(planData('<html></html>')).toBeNull();
	});

	it('gives minutes a day at the default 200 wpm, never below one', () => {
		expect(minutesPerDay({ total_words: 49318, day_count: 27 })).toBe(9);
		expect(minutesPerDay({ total_words: 50, day_count: 10 })).toBe(1);
		expect(minutesPerDay({ total_words: 100, day_count: 0 })).toBe(0);
	});
});
