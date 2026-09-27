import { describe, expect, it, vi } from 'vitest';

import { createResponseCache } from './buildFetch';

const API = 'https://api.example.org';
const get = (path: string, init?: RequestInit) => new Request(`${API}${path}`, init);

/** An API that answers each path with a body naming the path and a call count. */
function api(status = 200) {
	let calls = 0;
	return vi.fn(async (req: RequestInfo | URL) => {
		calls++;
		const body = JSON.stringify({ path: new URL((req as Request).url).pathname, call: calls });
		return new Response(body, {
			status,
			statusText: status === 200 ? 'OK' : 'Not Found',
			headers: { 'content-type': 'application/json' }
		});
	});
}

describe('createResponseCache', () => {
	it('stores a URL on its second request and answers later ones byte for byte', async () => {
		const fetch = api();
		const cached = createResponseCache(API);
		const url = '/api/library/books/?language=es';
		await cached(get(url), fetch); // first sighting: passed through, not stored
		const second = await (await cached(get(url), fetch)).text();
		const third = await cached(get(url), fetch);
		expect(fetch).toHaveBeenCalledTimes(2);
		expect(third.status).toBe(200);
		expect(third.statusText).toBe('OK');
		expect(await third.text()).toBe(second);
	});

	it('keeps a 404, which is a real answer', async () => {
		const fetch = api(404);
		const cached = createResponseCache(API);
		for (let i = 0; i < 3; i++) await cached(get('/api/library/books/x/?language=fr'), fetch);
		const again = await cached(get('/api/library/books/x/?language=fr'), fetch);
		expect(again.status).toBe(404);
		expect(again.statusText).toBe('Not Found');
		expect(fetch).toHaveBeenCalledTimes(2);
	});

	it('never keeps a 5xx, so the build retries reach the API', async () => {
		const cached = createResponseCache(API);
		const down = vi.fn(async () => new Response('boom', { status: 503 }));
		for (let i = 0; i < 3; i++) {
			expect((await cached(get('/api/library/topics/'), down)).status).toBe(503);
		}
		expect(down).toHaveBeenCalledTimes(3);
	});

	it('passes through anything that is not an anonymous API GET', async () => {
		const fetch = api();
		const cached = createResponseCache(API);
		const requests = () => [
			new Request('https://elsewhere.example/api/x/'),
			get('/api/library/search-click/', { method: 'POST', body: '{}' }),
			get('/api/auth/me/', { headers: { Authorization: 'Bearer t' } })
		];
		for (let i = 0; i < 3; i++) for (const req of requests()) await cached(req, fetch);
		expect(fetch).toHaveBeenCalledTimes(9);
	});

	it('stops storing once its byte cap is full, and still answers', async () => {
		const fetch = api();
		const cached = createResponseCache(API, 40); // room for one ~27-byte body
		for (const path of ['/api/a/', '/api/a/', '/api/b/', '/api/b/']) await cached(get(path), fetch);
		expect(fetch).toHaveBeenCalledTimes(4);
		await cached(get('/api/a/'), fetch); // stored
		await cached(get('/api/b/'), fetch); // over the cap: not stored, goes to the API
		expect(fetch).toHaveBeenCalledTimes(5);
	});
});
