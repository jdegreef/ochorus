/**
 * Let a tap paint before the work that doesn't show.
 *
 * INP counts from the tap to the next frame. Everything a handler does
 * synchronously — including bookkeeping the reader never sees (an analytics
 * beacon, a cache write) — sits between the two. A handler that updates the
 * state driving the visual change first and hands the rest to `afterPaint`
 * gets its feedback on screen a frame sooner.
 *
 * Only for work that may land a beat later: anything the next frame must
 * reflect stays in the handler.
 */

type Scheduler = { yield?: () => Promise<void> };

/**
 * Run `fn` after the browser has had a chance to paint. `scheduler.yield()`
 * where there is one (Chromium: its continuation runs ahead of other queued
 * tasks, so the work isn't starved); else the next frame plus a task, the
 * classic "after paint". A hidden page paints no frames, so it gets a plain
 * task — as does a page that is hidden before its frame comes, via a backstop
 * timer, so the work is never stranded.
 */
export function afterPaint(fn: () => void): void {
	const scheduler = (globalThis as { scheduler?: Scheduler }).scheduler;
	if (typeof scheduler?.yield === 'function') {
		scheduler.yield().then(fn);
		return;
	}
	if (
		typeof requestAnimationFrame !== 'function' ||
		(typeof document !== 'undefined' && document.visibilityState === 'hidden')
	) {
		setTimeout(fn, 0);
		return;
	}
	let done = false;
	const run = () => {
		if (done) return;
		done = true;
		fn();
	};
	requestAnimationFrame(() => setTimeout(run, 0));
	setTimeout(run, BACKSTOP_MS);
}

/** How long a frame may take to come before the work runs anyway. */
export const BACKSTOP_MS = 250;

/** `await yieldToMain()` inside an async handler: the same, as a promise. */
export function yieldToMain(): Promise<void> {
	return new Promise((resolve) => afterPaint(resolve));
}
