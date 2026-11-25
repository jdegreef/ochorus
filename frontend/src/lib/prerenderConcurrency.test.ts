import { describe, expect, it } from 'vitest';
import { prerenderConcurrency, RENDER_PRERENDER_CONCURRENCY } from '../../prerender-concurrency.js';

describe('prerenderConcurrency', () => {
	it('keeps Render at one page at a time, where the build crawls the live API', () => {
		expect(prerenderConcurrency({ RENDER_GIT_COMMIT: 'c28eecd' })).toBe(
			RENDER_PRERENDER_CONCURRENCY
		);
		// 3 in flight knocked the 512 MB API over mid-crawl (2026-11-25).
		expect(RENDER_PRERENDER_CONCURRENCY).toBe(1);
	});

	it('stays at one page at a time anywhere else', () => {
		expect(prerenderConcurrency({})).toBe(1);
		expect(prerenderConcurrency({ RENDER_GIT_COMMIT: '  ' })).toBe(1);
	});

	it('lets an explicit setting win, so CI can go wider and Render can roll back to 1', () => {
		expect(prerenderConcurrency({ PRERENDER_CONCURRENCY: '8' })).toBe(8);
		expect(prerenderConcurrency({ PRERENDER_CONCURRENCY: '1', RENDER_GIT_COMMIT: 'x' })).toBe(1);
	});

	it('ignores a setting that is not a positive whole number', () => {
		for (const bad of ['', '0', '-2', '2.5', 'lots']) {
			expect(prerenderConcurrency({ PRERENDER_CONCURRENCY: bad })).toBe(1);
			expect(prerenderConcurrency({ PRERENDER_CONCURRENCY: bad, RENDER_GIT_COMMIT: 'x' })).toBe(
				RENDER_PRERENDER_CONCURRENCY
			);
		}
	});
});
