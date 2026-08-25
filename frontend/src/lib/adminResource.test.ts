import { describe, it, expect, vi } from 'vitest';
import { ApiError } from './api';
import { AdminResource } from './adminResource.svelte';

/** A promise plus the handles to settle it later, so a test can interleave loads. */
function deferred<T>() {
	let resolve!: (v: T) => void;
	let reject!: (e: unknown) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	// A rejection that nothing awaits until later is still an unhandled rejection
	// to Node; this keeps the test runner from failing on our own scaffolding.
	promise.catch(() => {});
	return { promise, resolve, reject };
}

const settle = () => new Promise((r) => setTimeout(r, 0));

describe('AdminResource', () => {
	it('classifies 401 and 403 as denied, not as an error', async () => {
		for (const status of [401, 403]) {
			const r = new AdminResource(() => Promise.reject(new ApiError(status, null)), 'fallback');
			await r.load();
			expect(r.denied, `${status} should read as denied`).toBe(true);
			expect(r.error).toBe(null);
			expect(r.loading).toBe(false);
		}
	});

	it('reports any other failure as an error, keeping the message', async () => {
		const r = new AdminResource(() => Promise.reject(new ApiError(500, null)), 'fallback');
		await r.load();
		expect(r.denied).toBe(false);
		expect(r.error).toBe('API 500');
	});

	it('falls back to the supplied message when the failure carries none', async () => {
		const r = new AdminResource(() => Promise.reject('a bare string'), 'Could not load users.');
		await r.load();
		expect(r.error).toBe('Could not load users.');
	});

	it('clears a previous denial when a later load succeeds', async () => {
		let ok = false;
		const r = new AdminResource(
			() => (ok ? Promise.resolve({ n: 1 }) : Promise.reject(new ApiError(401, null))),
			'fallback'
		);
		await r.load();
		expect(r.denied).toBe(true);
		ok = true;
		await r.load();
		expect(r.denied).toBe(false);
		expect(r.data).toEqual({ n: 1 });
	});

	// The bug the sequence guard exists for, in the order it actually happens:
	// the page mounts and fires an ANONYMOUS request, auth settles and fires an
	// authenticated one, and the anonymous 401 lands last. Without the guard the
	// admin is told they aren't authorised while holding a loaded payload.
	it('ignores a stale rejection that lands after a newer success', async () => {
		const stale = deferred<{ n: number }>();
		const fresh = deferred<{ n: number }>();
		const calls = [stale, fresh];
		let i = 0;
		const r = new AdminResource(() => calls[i++].promise, 'fallback');

		const first = r.load();
		const second = r.load();

		fresh.resolve({ n: 2 });
		await second;
		stale.reject(new ApiError(401, null));
		await first;
		await settle();

		expect(r.denied, 'the superseded 401 must not deny a loaded page').toBe(false);
		expect(r.error).toBe(null);
		expect(r.data).toEqual({ n: 2 });
		expect(r.loading, 'the superseded load must not clear the newest load state').toBe(false);
	});

	it('ignores a stale success that lands after a newer one', async () => {
		const stale = deferred<{ n: number }>();
		const fresh = deferred<{ n: number }>();
		const calls = [stale, fresh];
		let i = 0;
		const r = new AdminResource(() => calls[i++].promise, 'fallback');

		const first = r.load();
		const second = r.load();

		fresh.resolve({ n: 2 });
		await second;
		stale.resolve({ n: 1 });
		await first;
		await settle();

		expect(r.data, 'the newest payload wins regardless of landing order').toEqual({ n: 2 });
	});

	it('leaves loading true while a newer load is still in flight', async () => {
		const stale = deferred<{ n: number }>();
		const fresh = deferred<{ n: number }>();
		const calls = [stale, fresh];
		let i = 0;
		const r = new AdminResource(() => calls[i++].promise, 'fallback');

		const first = r.load();
		r.load();

		stale.resolve({ n: 1 });
		await first;
		await settle();

		expect(r.loading, 'the second request has not answered yet').toBe(true);
		fresh.resolve({ n: 2 });
		await settle();
		expect(r.loading).toBe(false);
	});

	// The follow-up requests a detail page chains off its payload must not fire
	// for a language the reader has already navigated away from.
	it('does not run onLoad for a superseded payload', async () => {
		const stale = deferred<{ n: number }>();
		const fresh = deferred<{ n: number }>();
		const calls = [stale, fresh];
		let i = 0;
		const onLoad = vi.fn();
		const r = new AdminResource(() => calls[i++].promise, 'fallback', onLoad);

		const first = r.load();
		const second = r.load();

		fresh.resolve({ n: 2 });
		await second;
		stale.resolve({ n: 1 });
		await first;
		await settle();

		expect(onLoad).toHaveBeenCalledTimes(1);
		expect(onLoad).toHaveBeenCalledWith({ n: 2 });
	});

	it('keeps the previous payload on screen while refreshing', async () => {
		const first = deferred<{ n: number }>();
		const second = deferred<{ n: number }>();
		const calls = [first, second];
		let i = 0;
		const r = new AdminResource(() => calls[i++].promise, 'fallback');

		first.resolve({ n: 1 });
		await r.load();
		expect(r.data).toEqual({ n: 1 });

		r.load();
		// `loading && !data` is what the gate renders "Loading…" on, so a refresh
		// over existing data must keep the table up rather than blanking it.
		expect(r.loading).toBe(true);
		expect(r.data).toEqual({ n: 1 });
		second.resolve({ n: 2 });
		await settle();
		expect(r.data).toEqual({ n: 2 });
	});
});
