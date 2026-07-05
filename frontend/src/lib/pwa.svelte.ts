import { browser, dev } from '$app/environment';

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
 */
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
						this.offlineReady = true; // first ever install → now cached
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
