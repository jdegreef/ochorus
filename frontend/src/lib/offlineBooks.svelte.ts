import { browser } from '$app/environment';
import { preloadCode } from '$app/navigation';
import { reindexOffline } from './appOffline.svelte';
import { apiFetchText } from './api';
import { remoteAsset } from './assetUrl';
import { API_BASE_URL } from './config';
import { coverVariants } from './coverArt';
import { illustrationSrcs } from './illustrations';
import { bookApiPath, chapterApiPath } from './library-public';
import { newestFirst, OFFLINE_BOOKS_KEY, readOfflineList, type OfflineBook } from './offlineList';
import { writeJSON } from './persisted';
import { APP_ASSET_ORIGIN, IS_APP, offlineDelete, offlineSaveFile, offlineWriteText } from './platform';
import { apiFile, imageFile } from './platform/offlineFiles';

export type { OfflineBook };

/**
 * "Download for offline" — explicitly precache a whole book (its chapter API
 * responses + cover) into the durable `ochorus-offline` cache the service
 * worker serves first (see service-worker.ts). Unlike the opportunistic cache
 * (chapters you happen to open), a downloaded book survives deploys and covers
 * every chapter, so it's fully readable with no connection.
 *
 * A small metadata list in localStorage records what's downloaded so the UI can
 * show and manage it; the actual bytes live in the Cache API. This is a device
 * capability (like theme), not identity data — it isn't wiped on sign-out.
 *
 * The native app has no service worker (iOS's app web view runs none), so
 * there a download goes to the phone's own storage instead ($lib/platform's
 * offline files): the same book and chapter API responses, stored under the
 * very path $lib/api requests them by, and the same pictures, saved by their
 * site path. The metadata entry records both (`apiKeys`, `images`), and
 * $lib/appOffline answers from them — API reads before the network, images
 * through $lib/assetUrl. See MOBILE.md, "Offline books in the app".
 */

export const OFFLINE_CACHE = 'ochorus-offline';

/** What `download()` needs — a subset of BookDetail the book page already has. */
export interface DownloadableBook {
	slug: string;
	title: string;
	language: string;
	cover_url: string;
	author: { name: string };
	chapters: { order: number }[];
}

/**
 * The website needs the Cache API (its service worker answers from it); the
 * app stores on the phone instead, so it can always download.
 */
const supported = () => browser && (IS_APP || 'caches' in globalThis);

/**
 * A download is a book in ONE language, and always was in the bytes: every
 * cached URL carries `?language=`, and the metadata has recorded `language`
 * since this file was written. Only the TRACKING conflated them — `has()`, the
 * download dedupe and `remove()` all matched on slug alone — so downloading
 * "Humility" in English made the Spanish edition claim to be available offline
 * while its `?language=es` fetches missed the cache and failed, which the
 * reader discovered only once offline and could not then fix.
 *
 * Per-language rows under one slug ARE the content model (see CLAUDE.md);
 * per-slug tracking contradicted it.
 */
const sameEdition = (b: OfflineBook, slug: string, language: string) =>
	b.slug === slug && b.language === language;

/** The pictures a chapter's response shows (its body's illustrations). */
function chapterPictures(text: string): string[] {
	if (!text.includes('/illustrations/')) return [];
	const body = JSON.parse(text)?.body_html;
	return typeof body === 'string' ? illustrationSrcs(body) : [];
}

/** What a download recorded it stored (app only; see OfflineBook). */
type Stored = Pick<OfflineBook, 'apiKeys' | 'images'>;

/** What the app saves of a picture: a site path it would otherwise load from
 *  the website (`$lib/assetUrl`), with a safe file name. Bundled marks and
 *  absolute URLs are left alone. */
const appSavesImage = (path: string) =>
	!!path && remoteAsset(path, APP_ASSET_ORIGIN) !== path && imageFile(path) !== null;

/**
 * An in-app path matching the chapter route, for `preloadCode`. Trailing slash
 * because the route declares `trailingSlash = 'always'`; not localized, because
 * the module is the same one whatever locale prefixes the URL.
 */
const chapterPath = (slug: string, order: number) => `/books/${slug}/${order}/`;

/** `fn` over `items`, `n` at a time. */
async function inPool<T>(items: T[], n: number, fn: (item: T) => Promise<void>): Promise<void> {
	const queue = [...items];
	const worker = async () => {
		while (queue.length) await fn(queue.shift()!);
	};
	await Promise.all(Array.from({ length: Math.min(n, queue.length) }, worker));
}

class OfflineBooks {
	/** Bumped on any change so `list()` / `has()` re-derive. */
	ticks = $state(0);
	/** The in-flight download, for a progress indicator. */
	active = $state<{ slug: string; language: string; done: number; total: number } | null>(null);

	#load(): OfflineBook[] {
		return readOfflineList();
	}
	#save(list: OfflineBook[]) {
		writeJSON(OFFLINE_BOOKS_KEY, list);
		reindexOffline(list);
		this.ticks += 1;
	}

	#progress(book: DownloadableBook, total: number) {
		this.active = {
			slug: book.slug,
			language: book.language,
			done: (this.active?.done ?? 0) + 1,
			total
		};
	}

	/**
	 * The app's download: each API response written to the phone under its
	 * path, then the cover, its variants and the chapters' pictures saved there
	 * by site path. Returns what was stored, for the metadata entry. Best-effort
	 * per piece, as on the website: a chapter or picture that fails leaves the
	 * rest downloaded — and, downloading an edition AGAIN, keeps the copy the
	 * last download stored (`old`) rather than losing it to a flaky network.
	 * A few requests at a time; an illustrated book has dozens of files.
	 */
	async #saveToDevice(book: DownloadableBook, paths: string[], old?: OfflineBook): Promise<Stored> {
		const stored = new Set<string>();
		const pictures = new Set<string>();
		await inPool(paths, 4, async (path) => {
			try {
				const text = await apiFetchText(path);
				if (await offlineWriteText(apiFile(path), text)) stored.add(path);
				// paths[0] is the book itself; only chapters carry a body.
				if (path !== paths[0]) for (const src of chapterPictures(text)) pictures.add(src);
			} catch {
				/* one chapter failed — keep going; the rest still download */
			}
			this.#progress(book, paths.length);
		});
		const wanted = [...new Set([book.cover_url, ...coverVariants(book.cover_url), ...pictures])].filter(
			appSavesImage
		);
		const saved = new Set<string>();
		await inPool(wanted, 4, async (path) => {
			if (await offlineSaveFile(imageFile(path)!, `${APP_ASSET_ORIGIN}${path}`)) saved.add(path);
		});
		// A failed piece the last download had: its file is still there.
		for (const k of old?.apiKeys ?? []) if (paths.includes(k)) stored.add(k);
		for (const p of old?.images ?? []) if (wanted.includes(p)) saved.add(p);
		// In the order the book has them, not the order they arrived in.
		return { apiKeys: paths.filter((p) => stored.has(p)), images: wanted.filter((p) => saved.has(p)) };
	}

	/**
	 * The app's files of `entry` that none of `keep` also recorded. Each entry
	 * lists its own files, so the website's shared-file rules (in `remove`: a
	 * cover two editions wear, a work's pictures that all its editions show)
	 * reduce to one here — keep what a kept edition saved too.
	 */
	async #deleteFiles(entry: OfflineBook, keep: OfflineBook[]): Promise<void> {
		const keptApi = new Set(keep.flatMap((b) => b.apiKeys ?? []));
		const keptImages = new Set(keep.flatMap((b) => b.images ?? []));
		await offlineDelete([
			...(entry.apiKeys ?? []).filter((k) => !keptApi.has(k)).map(apiFile),
			...(entry.images ?? []).filter((p) => !keptImages.has(p)).flatMap((p) => imageFile(p) ?? [])
		]);
	}

	/** All downloaded books, newest first. Reads `ticks` so callers stay reactive. */
	list(): OfflineBook[] {
		this.ticks;
		return newestFirst(this.#load());
	}

	/** Whether this device can save a book for offline reading at all. */
	get supported(): boolean {
		return supported();
	}

	has(slug: string, language: string): boolean {
		this.ticks;
		return this.#load().some((b) => sameEdition(b, slug, language));
	}

	/** Precache a book. Requires a connection; a no-op if already downloading. */
	async download(book: DownloadableBook): Promise<boolean> {
		if (!supported() || this.active || !navigator.onLine) return false;
		const orders = book.chapters.map((c) => c.order);
		// The very paths $lib/api asks for (getBook, getChapterWithLang), so a
		// stored response answers the reader's own request.
		const paths = [
			bookApiPath(book.slug, book.language),
			...orders.map((o) => chapterApiPath(book.slug, o, book.language))
		];
		this.active = { slug: book.slug, language: book.language, done: 0, total: paths.length };
		try {
			const old = this.#load().find((b) => sameEdition(b, book.slug, book.language));
			// No `preloadCode` in the app: its code is all in the bundle.
			const stored = IS_APP ? await this.#saveToDevice(book, paths, old) : await this.#saveToCache(book, paths);
			// Replace only THIS edition's entry. Filtering on slug alone discarded
			// the other language's metadata while its cached bytes stayed behind —
			// an untracked download that nothing could then remove.
			const list = this.#load().filter((b) => !sameEdition(b, book.slug, book.language));
			// Downloading an edition again (app): what the old copy stored and the
			// book no longer has (a chapter since dropped, a redrawn cover's old
			// name) would otherwise stay on the phone with nothing to remove it.
			if (IS_APP && old) await this.#deleteFiles(old, [...list, { ...old, ...stored }]);
			list.push({
				slug: book.slug,
				title: book.title,
				author: book.author?.name ?? '',
				coverUrl: book.cover_url ?? '',
				language: book.language,
				chapterCount: orders.length,
				at: Date.now(),
				...stored
			});
			this.#save(list);
			return true;
		} finally {
			this.active = null;
		}
	}

	/** The website's download: into the Cache API the service worker serves. */
	async #saveToCache(book: DownloadableBook, paths: string[]): Promise<Stored> {
		const orders = book.chapters.map((c) => c.order);
		const urls = paths.map((p) => `${API_BASE_URL}${p}`);
		const cache = await caches.open(OFFLINE_CACHE);
		// Pictures the chapters show, collected as their text downloads and
		// cached after it — into the same durable cache, or an illustrated book
		// would read offline with a broken image wherever a plate stood.
		const pictures = new Set<string>();
		for (const [i, url] of urls.entries()) {
			try {
				const res = await fetch(url);
				if (res.ok) {
					await cache.put(url, res.clone());
					// urls[0] is the book itself; only chapters carry a body.
					if (i > 0) for (const src of chapterPictures(await res.text())) pictures.add(src);
				}
			} catch {
				/* one chapter failed — keep going; the rest still download */
			}
			this.#progress(book, urls.length);
		}
		// The chapter route's own MODULE, not just its data.
		//
		// `PRECACHE` deliberately holds only the entry chunks and stylesheets,
		// so the code that renders a chapter is fetched the first time one is
		// opened. A reader who downloaded a book without ever opening one of
		// its chapters therefore had every chapter's text and none of the code
		// that draws it: offline, the service worker served the SPA shell
		// correctly (#1072) and the shell then 500'd on a route module it had
		// never seen. Download for a flight, close the tab, open it on the
		// plane — an error page for a book the device holds in full.
		//
		// `preloadCode` imports the module, which puts it through the worker's
		// `cacheFirst` like any other same-origin asset. Best-effort: the
		// chapters are already cached by this point, and a reader who has read
		// any chapter of any book already has this module.
		if (orders.length) {
			try {
				await preloadCode(chapterPath(book.slug, orders[0]));
			} catch {
				/* route module unavailable — the text is still downloaded */
			}
		}

		// Cover (often cross-origin): best-effort, opaque is fine for <img>.
		//
		// The VARIANTS too, not just `cover_url`. `BookCover` asks for
		// `<cover>-320.webp` through srcset and never requests the original, so
		// caching that alone downloaded a file nothing then fetched: the variant
		// landed in the versioned cache instead, which `activate` drops on the
		// next deploy, and a downloaded book quietly lost its cover.
		const covers = [book.cover_url, ...coverVariants(book.cover_url)].filter(Boolean);
		for (const url of covers) {
			try {
				const res = await fetch(url, { mode: 'no-cors' });
				await cache.put(url, res.clone());
			} catch {
				/* cover unavailable — text still reads offline */
			}
		}
		// Independent and best-effort, so in parallel; one missing picture
		// leaves the rest (and the text) downloaded.
		await Promise.allSettled(
			[...pictures].map(async (url) => {
				const res = await fetch(url);
				if (res.ok) await cache.put(url, res);
			})
		);
		return {};
	}

	/** Remove one downloaded EDITION: drop its cached entries and untrack it. */
	async remove(slug: string, language: string): Promise<void> {
		if (!supported()) return;
		const meta = this.#load().find((b) => sameEdition(b, slug, language));
		const rest = this.#load().filter((b) => !sameEdition(b, slug, language));
		if (IS_APP) {
			if (meta) await this.#deleteFiles(meta, rest);
			this.#save(rest);
			return;
		}
		try {
			const cache = await caches.open(OFFLINE_CACHE);
			const marker = `/api/library/books/${slug}/`;
			for (const req of await cache.keys()) {
				const url = new URL(req.url);
				// The language too: matching the path alone would delete the OTHER
				// edition's chapters as collateral, leaving it tracked as downloaded
				// with nothing cached behind it.
				if (
					url.pathname.includes(marker) &&
					url.searchParams.get('language') === language
				) {
					await cache.delete(req);
				}
			}
			// The VARIANTS too, not just the original. `download()` caches all
			// three (BookCover's srcset only ever asks for a variant), so deleting
			// `coverUrl` alone left the bytes a render actually uses orphaned in
			// `ochorus-offline` — the durable cache `activate` deliberately never
			// clears. "Remove download" is the storage-reclaim button; it has to
			// reclaim what the download took, or every download/remove cycle
			// leaks on exactly the storage-pressured phones this is for.
			//
			// Unless an edition we are KEEPING wears the same file: a wordless
			// ground under /covers/art/ serves every language (see CLAUDE.md), so
			// two editions can share a cover_url, and deleting it here would
			// blank the one still downloaded.
			// Its pictures too: they live under one folder per WORK, so they are
			// shared by its editions — keep them while another edition of the same
			// work is still downloaded.
			if (!rest.some((b) => b.slug === slug)) {
				const pictures = `/illustrations/${slug}/`;
				for (const req of await cache.keys()) {
					if (new URL(req.url).pathname.startsWith(pictures)) await cache.delete(req);
				}
			}
			const stillUsed = new Set(rest.map((b) => b.coverUrl));
			if (meta?.coverUrl && !stillUsed.has(meta.coverUrl)) {
				for (const url of [meta.coverUrl, ...coverVariants(meta.coverUrl)]) {
					await cache.delete(url);
				}
			}
		} catch {
			/* cache unavailable — still untrack below */
		}
		this.#save(rest);
	}
}

export const offlineBooks = new OfflineBooks();
