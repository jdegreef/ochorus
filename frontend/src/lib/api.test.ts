import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// api.ts only retries while `building` — simulate a prerender build. (The
// default test stand-in in src/test/app-environment.ts has building=false.)
vi.mock('$app/environment', () => ({
	browser: false,
	dev: false,
	building: true,
	version: 'test'
}));

import { apiFetch, ApiError } from './api';

const ok = () =>
	new Response(JSON.stringify({ ok: true }), {
		status: 200,
		headers: { 'Content-Type': 'application/json' }
	});
const boom = () => new Response('boom', { status: 500 });

describe('apiFetch build-time retries', () => {
	let fetchMock: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		vi.useFakeTimers();
		fetchMock = vi.fn();
		vi.stubGlobal('fetch', fetchMock);
		vi.spyOn(console, 'warn').mockImplementation(() => {});
	});
	afterEach(() => {
		vi.unstubAllGlobals();
		vi.useRealTimers();
		vi.restoreAllMocks();
	});

	it('retries a transient 5xx and returns the eventual success', async () => {
		fetchMock.mockResolvedValueOnce(boom()).mockResolvedValueOnce(ok());
		const promise = apiFetch('/library/topics/');
		await vi.runAllTimersAsync();
		await expect(promise).resolves.toEqual({ ok: true });
		expect(fetchMock).toHaveBeenCalledTimes(2);
	});

	it('retries a network error and returns the eventual success', async () => {
		fetchMock
			.mockRejectedValueOnce(new TypeError('fetch failed'))
			.mockResolvedValueOnce(ok());
		const promise = apiFetch('/library/topics/');
		await vi.runAllTimersAsync();
		await expect(promise).resolves.toEqual({ ok: true });
		expect(fetchMock).toHaveBeenCalledTimes(2);
	});

	it('still fails the build on a persistent 5xx, after exhausting retries', async () => {
		fetchMock.mockImplementation(async () => boom());
		const promise = apiFetch('/library/topics/');
		const outcome = expect(promise).rejects.toBeInstanceOf(ApiError);
		await vi.runAllTimersAsync();
		await outcome;
		// One initial attempt plus one per backoff step.
		expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(3);
	});

	it('never retries a 4xx — a client error is not transient', async () => {
		fetchMock.mockResolvedValueOnce(new Response('nope', { status: 404 }));
		await expect(apiFetch('/library/topics/nope/')).rejects.toBeInstanceOf(ApiError);
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});

	it('never retries a non-idempotent request', async () => {
		fetchMock.mockResolvedValueOnce(boom());
		await expect(
			apiFetch('/library/thing/', { method: 'POST', body: '{}' })
		).rejects.toBeInstanceOf(ApiError);
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});
});
