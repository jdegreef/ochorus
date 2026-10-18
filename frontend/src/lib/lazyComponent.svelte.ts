import type { Component } from 'svelte';

/**
 * A component whose code loads on first use instead of with every page.
 *
 * The root layout mounts a handful of overlays — the ⌘K palette, the sign-up
 * sheet, the PWA toasts, One Tap — that most visits never open. Imported
 * statically, every page downloaded, parsed and hydrated them up front, which
 * is main-thread time an early tap waits behind (INP). Instead the layout keeps
 * the cheap TRIGGER (a flag, a shortcut) and calls `load()` when it fires:
 *
 *     const sheet = lazyComponent(() => import('$lib/components/Sheet.svelte'));
 *     $effect(() => { if (sheetUi.open) sheet.load(); });
 *     {#if sheet.component}<sheet.component />{/if}
 *
 * Once loaded the component stays mounted, so it keeps its state (a typed
 * email, a listener) exactly as a static mount did; the first open just mounts
 * it already open. A failed load (offline, a deploy replaced the chunk) is
 * logged and forgotten, so the next trigger tries again.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- props vary per component
export function lazyComponent<C extends Component<any>>(loader: () => Promise<{ default: C }>) {
	let component = $state<C>();
	let pending: Promise<C | undefined> | undefined;
	return {
		get component() {
			return component;
		},
		load(): Promise<C | undefined> {
			return (pending ??= loader().then(
				(m) => (component = m.default),
				(err) => {
					pending = undefined;
					console.error(err);
					return undefined;
				}
			));
		}
	};
}

/**
 * Run `fn` once the browser is idle after load — for chrome that must be
 * mounted before it is needed (a live region, a timed prompt) but not before
 * the page is interactive. `timeout` caps the wait on a page that never idles.
 */
export function onIdle(fn: () => void, timeout = 2000): () => void {
	const w = window as Window & {
		requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number;
		cancelIdleCallback?: (id: number) => void;
	};
	if (w.requestIdleCallback && w.cancelIdleCallback) {
		const id = w.requestIdleCallback(fn, { timeout });
		return () => w.cancelIdleCallback!(id);
	}
	const id = setTimeout(fn, Math.min(timeout, 1000));
	return () => clearTimeout(id);
}
