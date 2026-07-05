/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

/**
 * Ochorus offline service worker.
 *
 * Caching strategy:
 *  - App shell (hashed build chunks, fonts, CSS) → precached on install,
 *    served cache-first. These are immutable per `version`, so a new deploy
 *    ships a new cache and the old one is dropped on activate.
 *  - Navigations → network-first, falling back to the cached SPA shell so the
 *    app opens with no connection.
 *  - Book content (`/api/library/…`) → stale-while-revalidate: the reader gets
 *    an instant cached response and a fresh copy lands in the background, so any
 *    chapter you've opened before is readable offline.
 *  - Other same-origin assets (covers, icons) → cache-first, filled on demand.
 *
 * Registered manually from lib/pwa.svelte.ts (kit.serviceWorker.register=false)
 * so the client can prompt before applying an update rather than reloading under
 * the reader.
 */

import { build, files, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;

const CACHE = `ochorus-cache-${version}`;
const APP_SHELL = '/';

// Essential shell to precache: hashed build output (JS/CSS/fonts) + PWA assets.
// Covers and other static files are cached on demand to keep install fast.
const PRECACHE = [...build, '/manifest.json', '/icons/icon-192.png'];

sw.addEventListener('install', (event) => {
	event.waitUntil(
		(async () => {
			const cache = await caches.open(CACHE);
			await cache.addAll(PRECACHE);
			// Cache the SPA shell HTML so navigations work offline.
			try {
				const res = await fetch(APP_SHELL, { cache: 'reload' });
				if (res.ok) await cache.put(APP_SHELL, res.clone());
			} catch {
				/* offline at install time — shell caches on first online nav */
			}
		})()
	);
	// Do NOT skipWaiting here: the new worker waits until the user accepts.
});

sw.addEventListener('activate', (event) => {
	event.waitUntil(
		(async () => {
			for (const key of await caches.keys()) {
				if (key !== CACHE) await caches.delete(key);
			}
			await sw.clients.claim();
		})()
	);
});

// The client posts this to apply a pending update immediately.
sw.addEventListener('message', (event) => {
	if ((event.data as { type?: string })?.type === 'SKIP_WAITING') sw.skipWaiting();
});

const isLibraryApi = (url: URL) => url.pathname.includes('/api/library/');
const isPrecached = (url: URL) =>
	url.origin === sw.location.origin &&
	(build.includes(url.pathname) || PRECACHE.includes(url.pathname));

sw.addEventListener('fetch', (event) => {
	const { request } = event;
	if (request.method !== 'GET') return;

	const url = new URL(request.url);

	if (request.mode === 'navigate') {
		event.respondWith(networkThenShell(request));
		return;
	}
	if (isLibraryApi(url)) {
		event.respondWith(staleWhileRevalidate(request));
		return;
	}
	if (isPrecached(url) || url.origin === sw.location.origin) {
		event.respondWith(cacheFirst(request));
	}
});

async function cacheFirst(request: Request): Promise<Response> {
	const cache = await caches.open(CACHE);
	const cached = await cache.match(request);
	if (cached) return cached;
	try {
		const res = await fetch(request);
		if (res.ok && (res.type === 'basic' || res.type === 'cors')) {
			cache.put(request, res.clone());
		}
		return res;
	} catch {
		return cached ?? Response.error();
	}
}

async function networkThenShell(request: Request): Promise<Response> {
	const cache = await caches.open(CACHE);
	try {
		return await fetch(request);
	} catch {
		const shell = (await cache.match(APP_SHELL)) ?? (await cache.match('/200.html'));
		return shell ?? Response.error();
	}
}

async function staleWhileRevalidate(request: Request): Promise<Response> {
	const cache = await caches.open(CACHE);
	const cached = await cache.match(request);
	const network = fetch(request)
		.then((res) => {
			if (res.ok) cache.put(request, res.clone());
			return res;
		})
		.catch(() => cached);
	return cached ?? (network as Promise<Response>);
}
