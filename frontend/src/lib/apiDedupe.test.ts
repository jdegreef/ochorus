import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Runtime, not prerender: the dedupe and the timeout are browser-side
// behaviour, and api.ts's retry ladder only applies while `building`.
vi.mock('$app/environment', () => ({
	browser: true,
	dev: false,
	building: false,
	version: 'test'
}));

import { apiFetch, ApiError, setAuthTokenProvider } from './api';

/** A fetch that does not resolve until told, so requests genuinely overlap. */
function deferredFetch() {
	const resolvers: Array<(value: Response) => void> = [];
	const mock = vi.fn(
		() =>
			new Promise<Response>((resolve) => {
				resolvers.push(resolve);
			})
	);
	const settleAll = (body: unknown = { ok: true }) => {
		for (const resolve of resolvers.splice(0)) {
			resolve(
				new Response(JSON.stringify(body), {
					status: 200,
					headers: { 'Content-Type': 'application/json' }
				})
			);
		}
	};
	return { mock, settleAll };
}

describe('in-flight GET dedupe', () => {
	let fetchMock: ReturnType<typeof vi.fn>;
	let settleAll: (body?: unknown) => void;

	beforeEach(() => {
		setAuthTokenProvider(() => null);
		const d = deferredFetch();
		fetchMock = d.mock;
		settleAll = d.settleAll;
		vi.stubGlobal('fetch', fetchMock);
	});
	afterEach(() => {
		vi.unstubAllGlobals();
		setAuthTokenProvider(() => null);
	});

	it('collapses concurrent requests for the same path into one', async () => {
		// The homepage shape: several components asking for the same shelf at once.
		const all = Promise.all([
			apiFetch('/library/plans/'),
			apiFetch('/library/plans/'),
			apiFetch('/library/plans/')
		]);
		expect(fetchMock).toHaveBeenCalledTimes(1);
		settleAll();
		const [a, b, c] = await all;
		expect(a).toEqual({ ok: true });
		expect(b).toBe(a);
		expect(c).toBe(a);
	});

	it("uses a load's own fetch, and never shares its request", async () => {
		// A load's fetch must SEE its own request — that is what inlines the
		// response into the prerendered page — so it can't borrow a promise from
		// an in-flight global request (or another page's load) for the same path.
		const load = deferredFetch();
		const all = Promise.all([
			apiFetch('/library/plans/'),
			apiFetch('/library/plans/', {}, load.mock as typeof fetch)
		]);
		expect(fetchMock).toHaveBeenCalledTimes(1);
		expect(load.mock).toHaveBeenCalledTimes(1);
		settleAll();
		load.settleAll();
		await all;
	});

	it('does not collapse different paths', async () => {
		const all = Promise.all([apiFetch('/library/plans/'), apiFetch('/library/books/')]);
		expect(fetchMock).toHaveBeenCalledTimes(2);
		settleAll();
		await all;
	});

	it('asks again once the first request has settled', async () => {
		const first = apiFetch('/library/plans/');
		settleAll();
		await first;
		const second = apiFetch('/library/plans/');
		expect(fetchMock).toHaveBeenCalledTimes(2);
		settleAll();
		await second;
	});

	it('never shares a response between two readers', async () => {
		// Keyed by token as well as path: an anonymous response must not resolve
		// a signed-in request, or vice versa.
		setAuthTokenProvider(() => 'token-a');
		const a = apiFetch('/auth/me/');
		setAuthTokenProvider(() => 'token-b');
		const b = apiFetch('/auth/me/');
		expect(fetchMock).toHaveBeenCalledTimes(2);
		settleAll();
		await Promise.all([a, b]);
	});

	it("sends a load's library read without the token, so hydration can replay it", async () => {
		// The inlined response is matched on headers too: a signed-in reader's
		// Authorization header missed it and hydrated from the live API.
		setAuthTokenProvider(() => 'token-a');
		const load = deferredFetch();
		const authOf = (m: ReturnType<typeof vi.fn>, i: number) =>
			new Headers((m.mock.calls[i] as unknown as [string, RequestInit])[1].headers).get(
				'Authorization'
			);
		const all = Promise.all([
			apiFetch('/api/library/authors/hudson-taylor/?language=am', {}, load.mock as typeof fetch),
			apiFetch('/api/reading/progress/', {}, load.mock as typeof fetch),
			apiFetch('/api/library/authors/hudson-taylor/?language=am')
		]);
		expect(authOf(load.mock, 0)).toBeNull();
		expect(authOf(load.mock, 1)).toBe('Bearer token-a');
		expect(authOf(fetchMock, 0)).toBe('Bearer token-a');
		load.settleAll();
		settleAll();
		await all;
	});

	it('leaves writes alone', async () => {
		// Two POSTs are two intentions; collapsing them would drop one.
		const all = Promise.all([
			apiFetch('/library/search-click/', { method: 'POST', body: '{}' }),
			apiFetch('/library/search-click/', { method: 'POST', body: '{}' })
		]);
		expect(fetchMock).toHaveBeenCalledTimes(2);
		settleAll();
		await all;
	});

	it('a failed request does not poison the next one', async () => {
		vi.stubGlobal(
			'fetch',
			// A 404, not a network error: the runtime retry would absorb a one-off
			// network failure, and this test is about the in-flight map.
			vi.fn()
				.mockResolvedValueOnce(new Response('', { status: 404 }))
				.mockResolvedValue(
					new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } })
				)
		);
		await expect(apiFetch('/library/plans/')).rejects.toThrow('API 404');
		// The in-flight entry must have been cleared, or this would re-throw the
		// first failure forever.
		await expect(apiFetch('/library/plans/')).resolves.toEqual({});
	});

	it('attaches an abort signal so a hung request cannot spin forever', async () => {
		const done = apiFetch('/library/plans/');
		const init = fetchMock.mock.calls[0][1] as RequestInit;
		expect(init.signal).toBeInstanceOf(AbortSignal);
		settleAll();
		await done;
	});
});

describe('runtime retries', () => {
	let fetchMock: ReturnType<typeof vi.fn>;
	const ok = () =>
		new Response('{"ok":true}', { status: 200, headers: { 'Content-Type': 'application/json' } });
	const status = (code: number) => new Response('', { status: code });

	beforeEach(() => {
		vi.useFakeTimers();
		setAuthTokenProvider(() => null);
		fetchMock = vi.fn();
		vi.stubGlobal('fetch', fetchMock);
		vi.spyOn(console, 'warn').mockImplementation(() => {});
	});
	afterEach(() => {
		vi.unstubAllGlobals();
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	it('rides out a proxy 503 (an API restart) instead of failing the page', async () => {
		fetchMock.mockResolvedValueOnce(status(503)).mockResolvedValueOnce(ok());
		const p = apiFetch('/api/library/authors/hudson-taylor/?language=am');
		await vi.runAllTimersAsync();
		await expect(p).resolves.toEqual({ ok: true });
		expect(fetchMock).toHaveBeenCalledTimes(2);
	});

	it('retries a network error, and gives up after the ladder', async () => {
		fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
		const p = apiFetch('/api/library/books/');
		const settled = expect(p).rejects.toThrow('Failed to fetch');
		await vi.runAllTimersAsync();
		await settled;
		expect(fetchMock).toHaveBeenCalledTimes(3);
	});

	it('never retries a 500 — Django answered, and that is a bug to see', async () => {
		fetchMock.mockResolvedValue(status(500));
		const p = apiFetch('/api/library/books/');
		const settled = expect(p).rejects.toBeInstanceOf(ApiError);
		await vi.runAllTimersAsync();
		await settled;
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});

	it('never retries a write', async () => {
		fetchMock.mockResolvedValue(status(503));
		const p = apiFetch('/api/library/search-click/', { method: 'POST', body: '{}' });
		const settled = expect(p).rejects.toBeInstanceOf(ApiError);
		await vi.runAllTimersAsync();
		await settled;
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});

	it('stops once the request was aborted', async () => {
		const controller = new AbortController();
		fetchMock.mockImplementation(() => {
			controller.abort();
			return Promise.reject(new DOMException('aborted', 'AbortError'));
		});
		const p = apiFetch('/api/library/books/', { signal: controller.signal });
		const settled = expect(p).rejects.toThrow('aborted');
		await vi.runAllTimersAsync();
		await settled;
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});
});
