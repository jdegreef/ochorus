import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// No `$app/environment` mock here: the default test stand-in has building=false,
// which is the runtime path where withTimeout applies a request timeout. (The
// sibling api.test.ts mocks building=true to exercise the prerender retry loop,
// where the timeout is deliberately NOT applied — so the two concerns live in
// separate files.)
import { apiFetch } from './api';

const ok = () =>
	new Response(JSON.stringify({ ok: true }), {
		status: 200,
		headers: { 'Content-Type': 'application/json' }
	});

describe('apiFetch request timeout signal', () => {
	let fetchMock: ReturnType<typeof vi.fn>;
	let captured: AbortSignal | null | undefined;

	beforeEach(() => {
		captured = undefined;
		fetchMock = vi.fn((_url: string, init: RequestInit) => {
			captured = init.signal;
			return Promise.resolve(ok());
		});
		vi.stubGlobal('fetch', fetchMock);
	});
	afterEach(() => {
		vi.unstubAllGlobals();
		vi.restoreAllMocks();
	});

	it('attaches an AbortSignal to every runtime request and resolves normally', async () => {
		await expect(apiFetch('/library/topics/')).resolves.toEqual({ ok: true });
		expect(captured).toBeInstanceOf(AbortSignal);
	});

	it("combines a caller's own signal, so caller-abort still cancels the request", async () => {
		const caller = new AbortController();
		// A caller signal routes past the GET-dedupe path, straight to a request.
		await expect(apiFetch('/library/define/', { signal: caller.signal })).resolves.toEqual({
			ok: true
		});
		const combined = captured;
		expect(combined).toBeInstanceOf(AbortSignal);
		expect(combined?.aborted).toBe(false);
		caller.abort();
		expect(combined?.aborted).toBe(true);
	});

	describe('when AbortSignal.timeout / AbortSignal.any are unavailable (older Safari)', () => {
		// The regression this whole change guards: withTimeout used to call these
		// two static methods unconditionally, so on a Safari that lacks them EVERY
		// apiFetch threw a TypeError before it hit the network. Delete them and
		// prove the reader still works.
		let realTimeout: typeof AbortSignal.timeout;
		let realAny: typeof AbortSignal.any;

		beforeEach(() => {
			realTimeout = AbortSignal.timeout;
			realAny = AbortSignal.any;
			// @ts-expect-error — deleting a static to emulate an older engine.
			delete AbortSignal.timeout;
			// @ts-expect-error — same.
			delete AbortSignal.any;
		});
		afterEach(() => {
			AbortSignal.timeout = realTimeout;
			AbortSignal.any = realAny;
		});

		it('still fetches and resolves instead of throwing', async () => {
			await expect(apiFetch('/library/authors/')).resolves.toEqual({ ok: true });
			expect(captured).toBeInstanceOf(AbortSignal);
		});

		it('the fallback still links a caller signal so caller-abort propagates', async () => {
			const caller = new AbortController();
			await expect(apiFetch('/library/plans/', { signal: caller.signal })).resolves.toEqual({
				ok: true
			});
			const combined = captured;
			expect(combined?.aborted).toBe(false);
			caller.abort();
			expect(combined?.aborted).toBe(true);
		});

		it('the fallback timeout signal aborts once the timeout elapses', async () => {
			vi.useFakeTimers();
			try {
				await apiFetch('/library/sermons/');
				expect(captured?.aborted).toBe(false);
				// Longer than REQUEST_TIMEOUT_MS (15s); the fallback uses setTimeout,
				// which fake timers can advance deterministically.
				vi.advanceTimersByTime(20_000);
				expect(captured?.aborted).toBe(true);
			} finally {
				vi.useRealTimers();
			}
		});
	});
});
