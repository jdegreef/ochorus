import { browser } from '$app/environment';

/** How often a page left in view looks at the clock again. */
const EVERY = 5 * 60_000;

/**
 * Run `fn` with the time now, again whenever the page comes back into view,
 * and every few minutes while it stays in view — for whatever shows "today"
 * (a feast's flames, a writer's birthday candle), so a page left open over
 * midnight follows the reader's day. Never while hidden. Returns the cleanup
 * (for an `$effect` or `onMount`).
 */
export function watchToday(fn: (now: Date) => void): () => void {
	if (!browser) return () => {};
	const look = () => {
		if (document.visibilityState === 'visible') fn(new Date());
	};
	look();
	document.addEventListener('visibilitychange', look);
	const tick = setInterval(look, EVERY);
	return () => {
		document.removeEventListener('visibilitychange', look);
		clearInterval(tick);
	};
}
