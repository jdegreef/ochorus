import { afterEach, describe, expect, it, vi } from 'vitest';
import { searchPage } from './library-public';

/**
 * The request "show more" makes.
 *
 * The merged search is capped per type, so the only way past the cap — and the
 * only way a sort can mean what it says — is asking the server for one type
 * across all of its matches. That makes this URL load-bearing: an omitted
 * `type` silently falls back to the merged, capped list, and an omitted
 * `offset` re-fetches the page the reader already has, which reads as a
 * "show more" button that does nothing.
 */

function mockFetch() {
	const spy = vi.fn(
		async () =>
			new Response(
				JSON.stringify({ query: 'prayer', type: 'chapter', sort: 'relevance', offset: 0, results: [] }),
				{ status: 200, headers: { 'content-type': 'application/json' } }
			)
	);
	vi.stubGlobal('fetch', spy);
	return spy;
}

const paramsOf = (spy: ReturnType<typeof mockFetch>) => {
	const call = spy.mock.calls[0] as unknown as [string | URL];
	return new URL(String(call[0]), 'http://x').searchParams;
};

afterEach(() => vi.restoreAllMocks());

describe('searchPage request', () => {
	it('asks for one type, in the reader’s language', async () => {
		const spy = mockFetch();
		await searchPage('prayer', 'sw', 'chapter');
		const p = paramsOf(spy);
		expect(p.get('q')).toBe('prayer');
		expect(p.get('language')).toBe('sw');
		expect(p.get('type')).toBe('chapter');
	});

	it('sends the offset when paging', async () => {
		const spy = mockFetch();
		await searchPage('prayer', 'en', 'chapter', { offset: 40 });
		expect(paramsOf(spy).get('offset')).toBe('40');
	});

	it('omits offset and sort at their defaults', async () => {
		// Keeps the first page's URL identical to the plain one, so it hits the
		// same cache entry rather than looking like a different request.
		const spy = mockFetch();
		await searchPage('prayer', 'en', 'chapter', { offset: 0, sort: 'relevance' });
		const p = paramsOf(spy);
		expect(p.has('offset')).toBe(false);
		expect(p.has('sort')).toBe(false);
	});

	it('sends a non-default sort', async () => {
		const spy = mockFetch();
		await searchPage('prayer', 'en', 'book', { sort: 'newest' });
		expect(paramsOf(spy).get('sort')).toBe('newest');
	});

	it('encodes a query that would otherwise break the URL', async () => {
		const spy = mockFetch();
		await searchPage('grace & peace', 'en', 'sermon');
		expect(paramsOf(spy).get('q')).toBe('grace & peace');
	});
});
