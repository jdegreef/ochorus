import { browser, dev } from '$app/environment';
import { page } from '$app/stores';
import { get } from 'svelte/store';

/**
 * Progressive-web-app lifecycle: registers the service worker, tracks whether
 * the app is ready to use offline, whether a new version is waiting, and the
 * live online/offline status. The UI (PwaToasts) reads these to show an
 * "available offline" confirmation, an "update ready" prompt, and an offline
 * indicator.
 *
 * The service worker is only registered in production builds — running it under
 * the Vite dev server would serve stale, cache-first chunks and break HMR. In
 * dev we still track online/offline so the indicator can be exercised.
 *
 * A waiting update is applied automatically as soon as the reader isn't
 * mid-chapter (see #applyWhenSafe); the prompt is only the fallback for when
 * they are.
 */

// Reading surfaces, where a reload would cost the reader their place and cut
// off text-to-speech mid-sentence. Route ids are de-localized by the reroute
// hook, so these match in every language (/lg/books/x/1 included).
const READER_ROUTES = new Set(['/books/[slug]/[order]', '/sermons/[slug]']);

// When this tab last auto-applied an update. Belt-and-braces: if a deploy ever
// served two versions in turn, an unguarded auto-apply could reload in a loop,
// so a second one hard on the heels of the first is left to the prompt instead.
// Only back-to-back applies are suppressed — a genuine later deploy, minutes or
// days into a long-lived tab, still applies on its own.
const AUTO_APPLIED_AT_KEY = 'ochorus:pwa-auto-applied-at';
const LOOP_WINDOW_MS = 30_000;

/** How long the informational "ready to read offline" toast stays up. */
const OFFLINE_READY_MS = 8000;

class Pwa {
	/** True once the app shell + assets are cached (first successful install). */
	offlineReady = $state(false);
	/** True when a newer service worker is installed and waiting to take over. */
	updateReady = $state(false);
	/** Live connectivity. */
	online = $state(true);

	#waiting: ServiceWorker | null = null;
	#reloading = false;

	init() {
		if (!browser) return;
		this.online = navigator.onLine;
		addEventListener('online', () => (this.online = true));
		addEventListener('offline', () => (this.online = false));

		if (dev || !('serviceWorker' in navigator)) return;

		// A new worker took control → reload once so the fresh assets are used.
		navigator.serviceWorker.addEventListener('controllerchange', () => {
			if (this.#reloading) return;
			this.#reloading = true;
			location.reload();
		});

		// Register once the page has loaded. init() runs from onMount, which may be
		// after the load event has already fired — so register immediately in that
		// case rather than waiting for an event that will never come.
		if (document.readyState === 'complete') this.#register();
		else addEventListener('load', () => this.#register(), { once: true });
	}

	async #register() {
		try {
			const reg = await navigator.serviceWorker.register('/service-worker.js', {
				type: 'classic'
			});

			if (reg.waiting && navigator.serviceWorker.controller) this.#setWaiting(reg.waiting);

			reg.addEventListener('updatefound', () => {
				const installing = reg.installing;
				if (!installing) return;
				installing.addEventListener('statechange', () => {
					if (installing.state !== 'installed') return;
					if (navigator.serviceWorker.controller) {
						this.#setWaiting(installing); // update to an already-running app
					} else {
						// First ever install → now cached. Informational, with nothing to
						// act on once read, so it clears itself; the update and storage
						// toasts ask the reader to DO something and correctly persist
						// until dismissed.
						this.offlineReady = true;
						setTimeout(() => (this.offlineReady = false), OFFLINE_READY_MS);
					}
				});
			});
		} catch {
			/* SW blocked/unsupported — the app still works online */
		}
	}

	#setWaiting(worker: ServiceWorker) {
		this.#waiting = worker;
		this.updateReady = true;
		this.#applyWhenSafe();
	}

	/**
	 * Take a waiting update unless the reader is mid-chapter. Left to the prompt
	 * alone, an ignored update strands them on the old build indefinitely: the
	 * old worker keeps control for as long as any tab is open, so even a reload
	 * (or a locale switch, which is a full reload) still runs the old code.
	 */
	#applyWhenSafe() {
		if (!this.#waiting || this.#inReader()) return;
		const last = Number(sessionStorage.getItem(AUTO_APPLIED_AT_KEY)) || 0;
		if (Date.now() - last < LOOP_WINDOW_MS) return;
		sessionStorage.setItem(AUTO_APPLIED_AT_KEY, String(Date.now()));
		this.applyUpdate();
	}

	#inReader(): boolean {
		return READER_ROUTES.has(get(page).route.id ?? '');
	}

	/** Called after each client-side navigation: a page change is the natural
	 *  moment to take an update the reader was too busy for. */
	navigated() {
		if (browser && !dev) this.#applyWhenSafe();
	}

	/** Apply the waiting update; the controllerchange handler reloads the page. */
	applyUpdate() {
		this.updateReady = false;
		if (this.#waiting) this.#waiting.postMessage({ type: 'SKIP_WAITING' });
		else location.reload();
	}

	dismissOfflineReady() {
		this.offlineReady = false;
	}
}

export const pwa = new Pwa();
