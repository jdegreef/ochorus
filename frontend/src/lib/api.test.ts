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

describe('ApiError.body on a failed response', () => {
	// The body used to be read with `res.json()` and a `res.text()` fallback in
	// the catch — but a failed `res.json()` has already consumed the stream, so
	// the fallback always rejected and was swallowed into `null`. Every
	// non-JSON error body therefore arrived as `null`: exactly the HTML 502/503
	// pages a proxy serves during an outage, when the body is the only clue.
	let fetchMock: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		fetchMock = vi.fn();
		vi.stubGlobal('fetch', fetchMock);
	});
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	// A 4xx, deliberately: this file mocks `building: true`, so a 5xx would
	// enter the prerender retry loop and the test would be about backoff
	// instead of about the body. The body path is shared by every status.
	const failing = async (body: string, contentType?: string) => {
		fetchMock.mockResolvedValue(
			new Response(body, {
				status: 400,
				headers: contentType ? { 'Content-Type': contentType } : {}
			})
		);
		return apiFetch('/library/topics/').then(
			() => null,
			(e: unknown) => e as ApiError
		);
	};

	it('parses a JSON error body, so callers can still read .detail', async () => {
		const err = await failing(JSON.stringify({ detail: 'Not found.' }), 'application/json');
		expect(err?.body).toEqual({ detail: 'Not found.' });
	});

	it('keeps a NON-JSON body as text instead of losing it', async () => {
		// The regression: an HTML error page (what a proxy serves during an
		// outage) must survive to the error surface instead of becoming null.
		const html = '<html><body><h1>503 Service Unavailable</h1></body></html>';
		const err = await failing(html, 'text/html');
		expect(err?.body).toBe(html);
	});

	it('keeps a plain-text body', async () => {
		const err = await failing('upstream connect error');
		expect(err?.body).toBe('upstream connect error');
	});

	it('reports an empty body as null rather than an empty string', async () => {
		const err = await failing('');
		expect(err?.body).toBeNull();
	});
});
