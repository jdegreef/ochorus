import { browser } from '$app/environment';
import { API_BASE_URL } from './config';
import { coverVariants } from './coverArt';
import { readJSON, writeJSON } from './persisted';

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
 */

export const OFFLINE_CACHE = 'ochorus-offline';
const KEY = 'ochorus:offline-books';

export interface OfflineBook {
	slug: string;
	title: string;
	author: string;
	coverUrl: string;
	language: string;
	chapterCount: number;
	at: number;
}

/** What `download()` needs — a subset of BookDetail the book page already has. */
export interface DownloadableBook {
	slug: string;
	title: string;
	language: string;
	cover_url: string;
	author: { name: string };
	chapters: { order: number }[];
}

const supported = () => browser && 'caches' in globalThis;

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

function chapterUrl(slug: string, order: number, lang: string): string {
	return `${API_BASE_URL}/api/library/books/${slug}/chapters/${order}/?language=${lang}`;
}
function bookUrl(slug: string, lang: string): string {
	return `${API_BASE_URL}/api/library/books/${slug}/?language=${lang}`;
}

class OfflineBooks {
	/** Bumped on any change so `list()` / `has()` re-derive. */
	ticks = $state(0);
	/** The in-flight download, for a progress indicator. */
	active = $state<{ slug: string; language: string; done: number; total: number } | null>(null);

	#load(): OfflineBook[] {
		const raw = readJSON<OfflineBook[]>(KEY, []);
		return Array.isArray(raw) ? raw : [];
	}
	#save(list: OfflineBook[]) {
		writeJSON(KEY, list);
		this.ticks += 1;
	}

	/** All downloaded books, newest first. Reads `ticks` so callers stay reactive. */
	list(): OfflineBook[] {
		this.ticks;
		return [...this.#load()].sort((a, b) => b.at - a.at);
	}

	has(slug: string, language: string): boolean {
		this.ticks;
		return this.#load().some((b) => sameEdition(b, slug, language));
	}

	/** Precache a book. Requires a connection; a no-op if already downloading. */
	async download(book: DownloadableBook): Promise<boolean> {
		if (!supported() || this.active || !navigator.onLine) return false;
		const orders = book.chapters.map((c) => c.order);
		const urls = [bookUrl(book.slug, book.language), ...orders.map((o) => chapterUrl(book.slug, o, book.language))];
		this.active = { slug: book.slug, language: book.language, done: 0, total: urls.length };
		try {
			const cache = await caches.open(OFFLINE_CACHE);
			for (const url of urls) {
				try {
					const res = await fetch(url);
					if (res.ok) await cache.put(url, res.clone());
				} catch {
					/* one chapter failed — keep going; the rest still download */
				}
				this.active = {
					slug: book.slug,
					language: book.language,
					done: (this.active?.done ?? 0) + 1,
					total: urls.length
				};
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
			// Replace only THIS edition's entry. Filtering on slug alone discarded
			// the other language's metadata while its cached bytes stayed behind —
			// an untracked download that nothing could then remove.
			const list = this.#load().filter((b) => !sameEdition(b, book.slug, book.language));
			list.push({
				slug: book.slug,
				title: book.title,
				author: book.author?.name ?? '',
				coverUrl: book.cover_url ?? '',
				language: book.language,
				chapterCount: orders.length,
				at: Date.now()
			});
			this.#save(list);
			return true;
		} finally {
			this.active = null;
		}
	}

	/** Remove one downloaded EDITION: drop its cached entries and untrack it. */
	async remove(slug: string, language: string): Promise<void> {
		if (!supported()) return;
		const meta = this.#load().find((b) => sameEdition(b, slug, language));
		const rest = this.#load().filter((b) => !sameEdition(b, slug, language));
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
