import { browser } from '$app/environment';

/**
 * Run `fn` when the page stops being seen: hidden (a locked phone, a switched
 * tab) or being unloaded. Both, because an unload does not always fire
 * `visibilitychange` first, and a phone lock never fires `pagehide`. The last
 * chance to save and send anything — a timer set now may never run. Returns
 * the cleanup (for an `$effect`).
 */
export function onPageHidden(fn: () => void): () => void {
	if (!browser) return () => {};
	const onVisibility = () => {
		if (document.visibilityState === 'hidden') fn();
	};
	document.addEventListener('visibilitychange', onVisibility);
	window.addEventListener('pagehide', fn);
	return () => {
		document.removeEventListener('visibilitychange', onVisibility);
		window.removeEventListener('pagehide', fn);
	};
}

/**
 * Run `fn` now, and again each time the page comes back into view: the
 * reader's day may have turned while it was away (a tab left open over
 * midnight). The twin of onPageHidden, for whatever shows "today" — a
 * birthday candle, a feast's flames. Returns the cleanup (for an `$effect`).
 */
export function onPageShown(fn: () => void): () => void {
	if (!browser) return () => {};
	const onVisibility = () => {
		if (document.visibilityState === 'visible') fn();
	};
	onVisibility();
	document.addEventListener('visibilitychange', onVisibility);
	return () => document.removeEventListener('visibilitychange', onVisibility);
}
