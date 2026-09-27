import { afterEach, describe, expect, it, vi } from 'vitest';
import { listArticlesWithFallback } from './library-public';

const json = (body: unknown) =>
	new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } });

afterEach(() => vi.restoreAllMocks());

describe('listArticlesWithFallback', () => {
	it("names every article a reader can have read: their language's, then the English it falls back to", async () => {
		vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
			const url = String(input);
			if (url.includes('language=fr'))
				return json([{ slug: 'how-to-pray', h1: 'Comment prier' }]);
			return json([
				{ slug: 'how-to-pray', h1: 'How to Pray' },
				{ slug: 'what-is-faith', h1: 'What Is Faith?' }
			]);
		});
		const titles = Object.fromEntries(
			(await listArticlesWithFallback('fr')).map((a) => [a.slug, a.h1])
		);
		expect(titles).toEqual({ 'how-to-pray': 'Comment prier', 'what-is-faith': 'What Is Faith?' });
	});

	it('asks once for English, and a failed fetch is an empty list', async () => {
		const spy = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'));
		expect(await listArticlesWithFallback('en')).toEqual([]);
		expect(spy.mock.calls.filter(([u]) => String(u).includes('/articles/')).length).toBeGreaterThan(0);
	});
});
