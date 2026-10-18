import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { afterPaint, BACKSTOP_MS, yieldToMain } from './yieldToMain';

afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

describe('afterPaint with scheduler.yield', () => {
	it('runs the work in the yield continuation, never synchronously', async () => {
		let release!: () => void;
		const y = vi.fn(() => new Promise<void>((r) => (release = r)));
		vi.stubGlobal('scheduler', { yield: y });
		const fn = vi.fn();
		afterPaint(fn);
		expect(y).toHaveBeenCalledTimes(1);
		expect(fn).not.toHaveBeenCalled();
		release();
		await Promise.resolve();
		expect(fn).toHaveBeenCalledTimes(1);
	});
});

describe('afterPaint without scheduler.yield', () => {
	let frames: FrameRequestCallback[];
	beforeEach(() => {
		vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
		vi.stubGlobal('scheduler', undefined);
		frames = [];
		vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => frames.push(cb));
	});
	const frame = () => frames.splice(0).forEach((cb) => cb(0));

	it('waits for the next frame, then a task', () => {
		const fn = vi.fn();
		afterPaint(fn);
		vi.advanceTimersByTime(0);
		expect(fn).not.toHaveBeenCalled(); // no frame yet
		frame();
		expect(fn).not.toHaveBeenCalled(); // the frame paints first
		vi.advanceTimersByTime(0);
		expect(fn).toHaveBeenCalledTimes(1);
		// …and the backstop doesn't run it a second time.
		vi.advanceTimersByTime(BACKSTOP_MS);
		expect(fn).toHaveBeenCalledTimes(1);
	});

	it('runs on the backstop when no frame comes (the tab was hidden meanwhile)', () => {
		const fn = vi.fn();
		afterPaint(fn);
		vi.advanceTimersByTime(BACKSTOP_MS);
		expect(fn).toHaveBeenCalledTimes(1);
		frame();
		vi.advanceTimersByTime(0);
		expect(fn).toHaveBeenCalledTimes(1);
	});

	it('uses a plain task on a hidden page, which paints no frames', () => {
		const vis = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
		const fn = vi.fn();
		afterPaint(fn);
		expect(frames).toHaveLength(0);
		vi.advanceTimersByTime(0);
		expect(fn).toHaveBeenCalledTimes(1);
		vis.mockRestore();
	});

	it('keeps the order work was handed over in', () => {
		const order: number[] = [];
		afterPaint(() => order.push(1));
		afterPaint(() => order.push(2));
		frame();
		vi.advanceTimersByTime(0);
		expect(order).toEqual([1, 2]);
	});
});

describe('yieldToMain', () => {
	it('resolves after the yield', async () => {
		vi.stubGlobal('scheduler', { yield: () => Promise.resolve() });
		let done = false;
		const p = yieldToMain().then(() => (done = true));
		expect(done).toBe(false);
		await p;
		expect(done).toBe(true);
	});
});
