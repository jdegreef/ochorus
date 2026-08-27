/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

/**
 * Ochorus offline service worker.
 *
 * Two caches:
 *  - `ochorus-cache-<version>` (versioned) — the app shell (hashed build
 *    chunks, fonts, CSS) plus content cached *opportunistically* as you browse.
 *    Immutable per `version`; a new deploy ships a fresh one and the old is
 *    dropped on activate.
 *  - `ochorus-offline` (DURABLE) — content the reader *explicitly downloaded*
 *    for offline (a whole book's chapters + cover, via lib/offlineBooks). It is
 *    NOT version-suffixed, so a downloaded book survives deploys.
 *
 * Strategy:
 *  - App shell / build assets → precached, cache-first (versioned).
 *  - Navigations → network-first, falling back to the cached SPA shell so the
 *    app opens with no connection (the client then renders from cached data).
 *  - Book content (`/api/library/…`) → durable cache first (explicit
 *    downloads), else stale-while-revalidate into the versioned cache (so any
 *    chapter you've merely opened is also readable offline).
 *  - Cover images (often cross-origin) → durable cache first, else network.
 *  - Other same-origin assets → cache-first, filled on demand.
 *
 * Registered manually from lib/pwa.svelte.ts (kit.serviceWorker.register=false)
 * so the client can prompt before applying an update.
 */

import { build, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;

const CACHE = `ochorus-cache-${version}`;
const OFFLINE = 'ochorus-offline';

/**
 * The prerendered HOME page. A real document with home's own content and
 * embedded route data — so it is the right answer for a navigation to `/`, and
 * the wrong one for a navigation to anything else.
 */
const APP_SHELL = '/';

/**
 * The router-booting SPA fallback (`adapter-static`'s `fallback: '200.html'`,
 * see svelte.config.js). Unlike the prerendered `/`, it carries no route data
 * and renders whatever URL it is served at — which is exactly what an offline
 * deep link needs.
 *
 * `networkThenShell` always named this file, but nothing ever cached it, so the
 * match could not hit and every offline navigation fell through to `/`: a
 * reader who had explicitly downloaded a book got the homepage's HTML at their
 * chapter's URL, reachable only by then navigating from home by hand.
 */
const SPA_SHELL = '/200.html';

/**
 * What a first visit downloads before anything else.
 *
 * This was `[...build, ...]` — and `build` is EVERY artifact Vite emits: all
 * nine font families the reader offers as preferences, each in four unicode
 * subsets, plus every admin route chunk. A reader on a metered connection paid
 * for the whole application and for typefaces they will never select, in the
 * background, immediately after first paint.
 *
 * Now: the entry chunks and stylesheets that a first render actually needs.
 * Everything else still gets cached — the runtime `cacheFirst` handler fills it
 * in on demand — so offline support is unchanged for anything the reader has
 * actually opened, and a font is fetched when it is first chosen rather than
 * ahead of a choice nobody made.
 */
const isCritical = (path: string) =>
	path.endsWith('.css') || path.includes('/entry/') || path.includes('/chunks/');

const PRECACHE = [
	...build.filter(isCritical),
	'/manifest.json',
	'/icons/icon-192.png'
];

sw.addEventListener('install', (event) => {
	event.waitUntil(
		(async () => {
			const cache = await caches.open(CACHE);
			// allSettled, not addAll: addAll is atomic, so ONE artifact that
			// 404s aborts the whole install and the worker never activates —
			// turning a single missing file into no offline support at all.
			// A file that fails here is simply fetched on demand later.
			await Promise.allSettled(
				PRECACHE.map((path) => cache.add(path))
			);
			// Both shells, and neither is fatal: `ensureShells` re-tries on the
			// first successful navigation, so installing while offline no longer
			// leaves this worker version permanently without a fallback.
			await ensureShells(cache);
		})()
	);
	// Do NOT skipWaiting here: the new worker waits until the user accepts.
});

sw.addEventListener('activate', (event) => {
	event.waitUntil(
		(async () => {
			for (const key of await caches.keys()) {
				// Keep the current versioned cache AND the durable downloads cache.
				if (key !== CACHE && key !== OFFLINE) await caches.delete(key);
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
const isImage = (url: URL) => /\.(png|jpe?g|webp|avif|gif|svg)$/i.test(url.pathname);
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
		event.respondWith(offlineThenSWR(request));
		return;
	}
	if (isImage(url)) {
		event.respondWith(offlineThenImage(request));
		return;
	}
	// Never cache non-library API responses. When the API is same-origin (see
	// config.ts), the catch-all below would cache-first per-user, authenticated
	// endpoints like /api/auth/me/ and /api/reading/* — and the cache key ignores
	// the Authorization header, so a shared browser could serve one reader the
	// previous reader's profile/reading data. Let them go straight to the network.
	if (url.origin === sw.location.origin && url.pathname.includes('/api/')) return;
	if (isPrecached(url) || url.origin === sw.location.origin) {
		event.respondWith(cacheFirst(request));
	}
});

/** A hit in the durable downloads cache, if any. */
async function offlineHit(request: Request): Promise<Response | undefined> {
	return (await caches.open(OFFLINE)).match(request);
}

async function offlineThenSWR(request: Request): Promise<Response> {
	const downloaded = await offlineHit(request);
	if (downloaded) {
		// Refresh the durable copy in the background when online; never fatal.
		fetch(request)
			.then((res) => {
				if (res.ok) caches.open(OFFLINE).then((c) => c.put(request, res.clone()));
			})
			.catch(() => {});
		return downloaded;
	}
	return staleWhileRevalidate(request);
}

async function offlineThenImage(request: Request): Promise<Response> {
	const downloaded = await offlineHit(request);
	if (downloaded) return downloaded;
	// Cross-origin covers can't be safely stored in the versioned cache; just
	// pass through to the network (they show online, and offline once downloaded).
	if (new URL(request.url).origin !== sw.location.origin) {
		try {
			return await fetch(request);
		} catch {
			return Response.error();
		}
	}
	return cacheFirst(request);
}

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

/**
 * Cache the shell documents that aren't cached yet. A no-op once both are in.
 *
 * `ignoreVary` throughout: a static host commonly answers HTML with
 * `Vary: Accept-Encoding`, and a navigation whose `Accept-Encoding` differs
 * from the install-time fetch's would then MISS a shell that is sitting right
 * there — turning the offline fallback off for reasons no one could see. Any
 * cached copy of a shell is the copy we want.
 */
async function ensureShells(cache: Cache): Promise<void> {
	await Promise.allSettled(
		[SPA_SHELL, APP_SHELL].map(async (path) => {
			if (await cache.match(path, { ignoreVary: true })) return;
			const res = await fetch(path, { cache: 'reload' });
			if (res.ok) await cache.put(path, res.clone());
		})
	);
}

async function networkThenShell(request: Request): Promise<Response> {
	const cache = await caches.open(CACHE);
	try {
		const res = await fetch(request);
		// Online, so this is the moment to repair a shell the install couldn't
		// fetch. Best-effort and deliberately not awaited: the response must not
		// wait on it, and a miss just retries on the next navigation.
		void ensureShells(cache);
		return res;
	} catch {
		// An exact prerendered copy of THIS url beats either shell — it carries
		// the page's own content and data. (Home is such a copy of itself, which
		// is why `/` is no longer consulted first: it is the right answer for `/`
		// and the wrong one everywhere else.)
		const exact = await cache.match(request, { ignoreVary: true });
		if (exact) return exact;
		// Then the route-agnostic fallback, and only then home — which at least
		// boots the app, even though it renders home's data at the wrong URL.
		const shell =
			(await cache.match(SPA_SHELL, { ignoreVary: true })) ??
			(await cache.match(APP_SHELL, { ignoreVary: true }));
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
