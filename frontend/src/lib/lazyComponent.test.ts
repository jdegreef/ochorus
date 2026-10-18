import { describe, expect, it, vi, afterEach } from 'vitest';
import type { Component } from 'svelte';
import { lazyComponent, onIdle } from './lazyComponent.svelte';

const Fake = (() => {}) as unknown as Component;

describe('lazyComponent', () => {
	it('has no component until load() is called, then loads once', async () => {
		const loader = vi.fn(async () => ({ default: Fake }));
		const lazy = lazyComponent(loader);
		expect(lazy.component).toBeUndefined();
		expect(loader).not.toHaveBeenCalled();

		const [a, b] = await Promise.all([lazy.load(), lazy.load()]);
		expect(a).toBe(Fake);
		expect(b).toBe(Fake);
		expect(lazy.component).toBe(Fake);
		await lazy.load();
		expect(loader).toHaveBeenCalledTimes(1);
	});

	it('forgets a failed load so the next trigger retries', async () => {
		const err = vi.spyOn(console, 'error').mockImplementation(() => {});
		const loader = vi
			.fn<() => Promise<{ default: Component }>>()
			.mockRejectedValueOnce(new Error('chunk gone'))
			.mockResolvedValueOnce({ default: Fake });
		const lazy = lazyComponent(loader);

		await expect(lazy.load()).resolves.toBeUndefined();
		expect(lazy.component).toBeUndefined();
		expect(err).toHaveBeenCalled();

		await expect(lazy.load()).resolves.toBe(Fake);
		expect(lazy.component).toBe(Fake);
		expect(loader).toHaveBeenCalledTimes(2);
		err.mockRestore();
	});
});

describe('onIdle', () => {
	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	it('uses requestIdleCallback with the timeout when there is one', () => {
		const ric = vi.fn(() => 7);
		const cic = vi.fn();
		vi.stubGlobal('requestIdleCallback', ric);
		vi.stubGlobal('cancelIdleCallback', cic);
		const fn = vi.fn();
		const cancel = onIdle(fn, 1500);
		expect(ric).toHaveBeenCalledWith(fn, { timeout: 1500 });
		cancel();
		expect(cic).toHaveBeenCalledWith(7);
	});

	it('falls back to a timer (Safari has no requestIdleCallback), and can be cancelled', () => {
		vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
		vi.stubGlobal('requestIdleCallback', undefined);
		vi.stubGlobal('cancelIdleCallback', undefined);
		const fn = vi.fn();
		onIdle(fn);
		vi.advanceTimersByTime(1000);
		expect(fn).toHaveBeenCalledTimes(1);

		const never = vi.fn();
		onIdle(never)();
		vi.advanceTimersByTime(5000);
		expect(never).not.toHaveBeenCalled();
	});
});
