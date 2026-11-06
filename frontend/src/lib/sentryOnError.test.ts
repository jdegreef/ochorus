import { describe, expect, it, vi } from 'vitest';
import { BUFFER_LIMIT, armSentryOnError, isOwnError } from './sentryOnError';

/** A window stand-in that records listeners and lets a test fire events. */
function fakeTarget() {
	const listeners = new Map<string, Set<(e: Event) => void>>();
	return {
		addEventListener: (type: string, fn: (e: Event) => void) => {
			if (!listeners.has(type)) listeners.set(type, new Set());
			listeners.get(type)!.add(fn);
		},
		removeEventListener: (type: string, fn: (e: Event) => void) => listeners.get(type)?.delete(fn),
		fire: (type: string, init: Record<string, unknown>) =>
			listeners.get(type)?.forEach((fn) => fn(init as unknown as Event)),
		count: (type: string) => listeners.get(type)?.size ?? 0
	};
}

const flush = () => new Promise((r) => setTimeout(r, 0));
const OURS = [/\/_app\/immutable\//];

describe('armSentryOnError', () => {
	it('does not load the SDK until an error happens', () => {
		const load = vi.fn();
		armSentryOnError({ load, target: fakeTarget() as never });
		expect(load).not.toHaveBeenCalled();
	});

	it('loads once on the first error and hands over every held error', async () => {
		const t = fakeTarget();
		const sdk = { captureException: vi.fn() };
		const load = vi.fn(() => Promise.resolve(sdk));
		armSentryOnError({ load, allowUrls: OURS, target: t as never });
		const a = new Error('a');
		const b = new Error('b');
		t.fire('error', { error: a, filename: 'https://ochorus.com/_app/immutable/chunks/x.js' });
		t.fire('unhandledrejection', { reason: b });
		await flush();
		expect(load).toHaveBeenCalledTimes(1);
		expect(sdk.captureException.mock.calls.map((c) => c[0])).toEqual([a, b]);
		// Sentry's own handlers own new errors now: ours are gone.
		expect(t.count('error')).toBe(0);
		expect(t.count('unhandledrejection')).toBe(0);
	});

	it("ignores an extension's error without loading the SDK", async () => {
		const t = fakeTarget();
		const load = vi.fn();
		armSentryOnError({ load, allowUrls: OURS, target: t as never });
		t.fire('error', { error: new Error('x'), filename: 'chrome-extension://abc/content.js' });
		await flush();
		expect(load).not.toHaveBeenCalled();
		expect(t.count('error')).toBe(1);
	});

	it('holds at most BUFFER_LIMIT errors while the SDK downloads', async () => {
		const t = fakeTarget();
		const sdk = { captureException: vi.fn() };
		let resolve!: (s: typeof sdk) => void;
		const load = vi.fn(() => new Promise<typeof sdk>((r) => (resolve = r)));
		armSentryOnError({ load, target: t as never });
		for (let i = 0; i < BUFFER_LIMIT + 5; i++) t.fire('unhandledrejection', { reason: i });
		resolve(sdk);
		await flush();
		expect(load).toHaveBeenCalledTimes(1);
		expect(sdk.captureException).toHaveBeenCalledTimes(BUFFER_LIMIT);
	});

	it('stops listening if the SDK fails to load', async () => {
		const t = fakeTarget();
		armSentryOnError({ load: () => Promise.reject(new Error('blocked')), target: t as never });
		t.fire('unhandledrejection', { reason: 1 });
		await flush();
		expect(t.count('unhandledrejection')).toBe(0);
	});
});

describe('isOwnError', () => {
	it('treats a missing filename as ours', () => {
		expect(isOwnError({ filename: '' }, OURS)).toBe(true);
	});
	it('accepts everything without a pattern list (dev)', () => {
		expect(isOwnError({ filename: 'http://localhost:5173/src/x.ts' })).toBe(true);
	});
});
