/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

/**
 * Ochorus offline service worker.
 *
 * Caches:
 *  - `ochorus-cache-<version>` (versioned) — the app shell (hashed build
 *    chunks, fonts, CSS) plus content cached *opportunistically* as you browse.
 *    Immutable per `version`; a new deploy ships a fresh one and the old is
 *    dropped on activate.
 *  - `ochorus-pages-<version>` (versioned, capped) — page documents you have
 *    visited, for a slow or absent network (see `networkThenShell`).
 *  - `ochorus-images` (durable, capped) — same-origin covers and portraits.
 *  - `ochorus-offline` (DURABLE) — content the reader *explicitly downloaded*
 *    for offline (a whole book's chapters + cover, via lib/offlineBooks). It is
 *    NOT version-suffixed, so a downloaded book survives deploys.
 *
 * Strategy:
 *  - App shell / build assets → precached, cache-first (versioned).
 *  - Navigations → network-first (with navigation preload), settling for this
 *    page's own cached copy when the network is slow or gone, else the cached
 *    SPA shell so the app opens with no connection (the client then renders
 *    from cached data).
 *  - Book content (`/api/library/…`) → durable cache first (explicit
 *    downloads), else stale-while-revalidate into the versioned cache (so any
 *    chapter you've merely opened is also readable offline).
 *  - Cover images (often cross-origin) → durable downloads cache first; then
 *    same-origin ones from `ochorus-images`, refreshed in the background once
 *    a copy is an hour old, and cross-origin ones straight from the network.
 *  - Other same-origin assets → cache-first, filled on demand.
 *
 * Registered manually from lib/pwa.svelte.ts (kit.serviceWorker.register=false)
 * so the client can prompt before applying an update.
 */

import { build, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;

const CACHE = `ochorus-cache-${version}`;
const OFFLINE = 'ochorus-offline';
const PAGES = `ochorus-pages-${version}`;
const IMAGES = 'ochorus-images';

/**
 * Entry caps for the caches that fill as you browse. Without one the image
 * cache — durable on purpose, so a deploy (several a day) doesn't make a
 * returning reader re-download every cover — would only ever grow. Trimmed
 * oldest-write-first: `cache.keys()` is in insertion order and a re-`put`
 * moves an entry to the end, so what goes is what you haven't seen lately.
 */
const PAGE_LIMIT = 60;
const IMAGE_LIMIT = 300;

/**
 * How long a cached image is used without asking the network (see imageSWR).
 * The same hour render.yaml gives /covers, /portraits and /illustrations
 * (`max-age=3600`): the promise that a redrawn cover reaches a returning reader
 * within about an hour. Change the two together — a longer window here would
 * quietly override that header for every reader with the worker installed.
 */
const IMAGE_FRESH_MS = 3600 * 1000;
const FETCHED_AT = 'x-ochorus-fetched-at';

/**
 * How long a navigation waits on the network before settling for this page's
 * cached copy. Not stale-while-revalidate, deliberately: a cached page belongs
 * to the build it was fetched under, and once the server has moved to a newer
 * deploy the chunks that page has not loaded yet (a lazy drawer, the next
 * route) are gone from it. A fresh network page is never wrong, so it stays
 * the default; the cached copy only answers a connection too slow to do better.
 */
const NAV_TIMEOUT_MS = 2500;

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
// Not the per-locale font sheets: Korean's alone is ~100 KB of @font-face rules
// linked only on Korean pages (see $lib/fonts-ko.css), and every `fonts-*.css`
// is split out the same way. Precaching one would charge every reader who
// installs the worker for the very cost it was split out of app.css to avoid;
// a reader gets their locale's sheet on its first page, like any other asset.
const isCritical = (path: string) =>
	(path.endsWith('.css') && !/\/fonts-[^/]*$/.test(path)) ||
	path.includes('/entry/') ||
	path.includes('/chunks/');

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
				// Keep the current versioned caches AND the durable ones.
				if (![CACHE, PAGES, OFFLINE, IMAGES].includes(key)) await caches.delete(key);
			}
			// The network leg of a navigation now starts in parallel with booting
			// this worker instead of after it — the boot was pure added latency on
			// every network-first page load. Handed back as `preloadResponse`.
			await sw.registration.navigationPreload?.enable().catch(() => {});
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
		event.respondWith(networkThenShell(event));
		return;
	}
	if (isLibraryApi(url)) {
		event.respondWith(offlineThenSWR(request));
		return;
	}
	// SvelteKit's own deploy detector: `updated.check()` fetches this with
	// no-cache headers, which the cache-first catch-all below ignored — so once
	// cached it answered "no new version" for the life of this worker, and the
	// client's recovery from a route chunk a redeploy removed (reload onto the
	// new build) could never fire. Straight to the network.
	if (url.origin === sw.location.origin && url.pathname === '/_app/version.json') return;
	// Build images (`/_app/immutable/…`, named by their bytes) and the precached
	// icon live in the versioned cache, so the cache-first path below is right
	// for them; only content images can change under one URL and need refreshing.
	if (isImage(url) && !isPrecached(url)) {
		event.respondWith(offlineThenImage(event));
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

async function offlineThenImage(event: FetchEvent): Promise<Response> {
	const { request } = event;
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
	return imageSWR(event);
}

/**
 * Same-origin content images: durable, capped, refreshed at most hourly. Durable
 * because they don't change with a deploy, so dropping them with the versioned
 * cache made every returning reader re-fetch every cover several times a day.
 * Refreshed because they CAN change under one URL (a regenerated cover), so a
 * plain cache-first copy could be stale for good — but only once a copy is an
 * hour old, so a shelf of covers costs no requests on a same-session revisit.
 * A stale copy still answers at once; the refresh is for the next view.
 */
async function imageSWR(event: FetchEvent): Promise<Response> {
	const { request } = event;
	const cached = await (await caches.open(IMAGES)).match(request);
	if (cached && Date.now() - Number(cached.headers.get(FETCHED_AT)) < IMAGE_FRESH_MS) {
		return cached;
	}
	const network = fetch(request);
	// The page never reads a refresh it isn't shown, so that one is stored
	// as is; a response the page DOES read is copied before it can.
	event.waitUntil(
		network.then((res) => keepImage(request, cached ? res : res.clone())).catch(() => {})
	);
	return cached ?? network.catch(() => Response.error());
}

/**
 * Store an image stamped with when it was fetched — our own clock, not its
 * `Date` header, which on a copy from the browser's HTTP cache is the date the
 * server first sent it and would make a refreshed copy look stale at once.
 */
async function keepImage(request: Request, res: Response): Promise<void> {
	if (!res.ok || res.type !== 'basic') return;
	const headers = new Headers(res.headers);
	headers.set(FETCHED_AT, String(Date.now()));
	const stamped = new Response(res.body, {
		status: res.status,
		statusText: res.statusText,
		headers
	});
	await putCapped(IMAGES, request, stamped, IMAGE_LIMIT);
}

/**
 * Store a response in a capped cache, dropping the oldest entries beyond
 * `limit` (insertion order; see PAGE_LIMIT). Only a NEW key can grow the cache,
 * so a refresh of one already held skips the `keys()` walk — which on the image
 * cache would otherwise run on every cover shown.
 */
async function putCapped(name: string, request: Request, res: Response, limit: number) {
	const cache = await caches.open(name);
	// Without ignoreVary: exactly the entry `put` would replace, if any.
	const grows = !(await cache.match(request));
	await cache.put(request, res);
	if (!grows) return;
	const keys = await cache.keys();
	await Promise.all(keys.slice(0, Math.max(0, keys.length - limit)).map((k) => cache.delete(k)));
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

/** The navigation's network response — the preload, when there is one. */
async function navigationFetch(event: FetchEvent): Promise<Response> {
	try {
		const preloaded = (await event.preloadResponse) as Response | undefined;
		if (preloaded) return preloaded;
	} catch {
		/* preload failed — a plain fetch reports the real outcome */
	}
	return fetch(event.request);
}

/**
 * The build files a page document loads: entry, route chunks, stylesheets (and
 * `/_app/env.js` in the SPA fallback). Root-absolute, as `paths.relative` is off.
 */
const PAGE_ASSET = /\/_app\/[\w./-]+?\.(?:js|css)(?=["'\s)?#])/g;

/**
 * Keep a copy of a page document the network just served. Only a plain 200
 * HTML page: never a redirect (Chrome refuses a redirected response for a
 * navigation), never a query string (the static host ignores it, so each
 * variant would only evict a real page). Every document this site serves is
 * the same for every reader — a prerendered page or the SPA fallback — so a
 * cached one shares nothing personal.
 */
async function rememberPage(request: Request, res: Response): Promise<void> {
	if (!res.ok || res.type !== 'basic' || res.redirected) return;
	if (new URL(request.url).search) return;
	if (!res.headers.get('content-type')?.includes('text/html')) return;
	await putCapped(PAGES, request, res, PAGE_LIMIT);
}

/**
 * This URL's cached page — but only if every build file it loads is cached
 * too. That is what makes serving it safe across a deploy: hashed chunks are
 * named by their bytes, so a page whose chunks are all on hand hydrates
 * whatever build the server now holds, and one missing any (its tab closed
 * before they loaded, or a newer build's page stored but never rendered here)
 * is passed over rather than served as markup that can't come alive.
 *
 * What the HTML doesn't name, it can't check — a chunk imported later. A lazy
 * component's is under `/chunks/`, which install precaches whole (`isCritical`),
 * so it is on hand too. The next route's `/nodes/` file may not be; if a
 * redeploy took it, SvelteKit's router sees the new `version.json` (never
 * cached, see the fetch handler) and reloads onto the new build instead.
 */
async function completePage(request: Request): Promise<Response | undefined> {
	const page = await (await caches.open(PAGES)).match(request, { ignoreVary: true });
	if (!page) return undefined;
	const assets = new Set((await page.clone().text()).match(PAGE_ASSET));
	const shell = await caches.open(CACHE);
	const present = await Promise.all(
		[...assets].map((path) => shell.match(path, { ignoreVary: true }))
	);
	return present.every(Boolean) ? page : undefined;
}

async function networkThenShell(event: FetchEvent): Promise<Response> {
	const { request } = event;
	const network = navigationFetch(event);
	// Online, so keep this page and repair a shell the install couldn't fetch.
	// Registered before anything reads the body, so the clone is taken first
	// (and before any await, so a failed network is never briefly unhandled);
	// handed to `waitUntil` rather than left floating: the response must not
	// wait on it, but the worker may be terminated as soon as the response
	// settles — which would abort the very fetch the shell self-heal depends
	// on, silently and only for readers who first loaded offline.
	event.waitUntil(
		network
			// Independent: a page that can't be stored (a full disk) must not cost
			// the shell repair.
			.then((res) =>
				Promise.allSettled([
					rememberPage(request, res.clone()),
					caches.open(CACHE).then(ensureShells)
				])
			)
			.catch(() => {})
	);
	// A slow network loses to this page's own complete cached copy; with no such
	// copy, wait for the network however long it takes. The timer is cleared
	// once the network answers, so a fast load never reads the cached page.
	let timer: ReturnType<typeof setTimeout> | undefined;
	const slow = new Promise((resolve) => (timer = setTimeout(resolve, NAV_TIMEOUT_MS))).then(() =>
		completePage(request)
	);
	const settle = () => clearTimeout(timer);
	network.then(settle, settle);
	try {
		return (await Promise.race([network, slow])) ?? (await network);
	} catch {
		// An exact cached copy of THIS url beats either shell — it carries the
		// page's own content and data. (Home is such a copy of itself, which is
		// why `/` is no longer consulted first: it is the right answer for `/`
		// and the wrong one everywhere else.)
		const exact = await completePage(request);
		if (exact) return exact;
		// Then the route-agnostic fallback, and only then home — which at least
		// boots the app, even though it renders home's data at the wrong URL.
		const cache = await caches.open(CACHE);
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
