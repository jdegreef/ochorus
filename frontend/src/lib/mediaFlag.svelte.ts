/**
 * A media query as a reactive boolean that is `false` until the page has
 * hydrated — the hydration-safe flag the book reader, the sermon page and the
 * /scripture hub each grew their own copy of.
 *
 * NOT svelte/reactivity's `MediaQuery`: that reads matchMedia DURING
 * hydration, so on a phone an `{#if}` on it disagrees with the prerendered
 * (desktop) markup. This starts false (the prerendered answer), then flips in
 * an effect, after hydration, and follows changes (rotation, resizing).
 *
 * `query` may be a getter, for a query built from props (it is re-read, and
 * the listener swapped, when they change).
 *
 * Call it once from a component's `<script>` (it owns an `$effect`, so it must
 * run during component init, like `scrollSpy`). Anything that must be right on
 * the very first paint belongs in CSS instead — this is for choosing what to
 * MOUNT, not how it looks.
 */
export function mediaFlag(query: string | (() => string)) {
	let matches = $state(false);
	$effect(() => {
		const mq = window.matchMedia(typeof query === 'function' ? query() : query);
		const sync = () => (matches = mq.matches);
		sync();
		mq.addEventListener('change', sync);
		return () => mq.removeEventListener('change', sync);
	});
	return {
		get matches() {
			return matches;
		}
	};
}
