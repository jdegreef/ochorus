import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Runtime, not prerender: the dedupe and the timeout are browser-side
// behaviour, and api.ts's retry ladder only applies while `building`.
vi.mock('$app/environment', () => ({
	browser: true,
	dev: false,
	building: false,
	version: 'test'
}));

import { apiFetch, setAuthTokenProvider } from './api';

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
			vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(
				new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } })
			)
		);
		await expect(apiFetch('/library/plans/')).rejects.toThrow('offline');
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
