import { describe, expect, it } from 'vitest';
import { prerenderConcurrency, RENDER_PRERENDER_CONCURRENCY } from '../../prerender-concurrency.js';

describe('prerenderConcurrency', () => {
	it('overlaps a few requests on Render, where the build crawls the live API', () => {
		expect(prerenderConcurrency({ RENDER_GIT_COMMIT: 'c28eecd' })).toBe(
			RENDER_PRERENDER_CONCURRENCY
		);
		// One gunicorn worker with 4 threads serves the crawl and readers alike.
		expect(RENDER_PRERENDER_CONCURRENCY).toBeLessThan(4);
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
