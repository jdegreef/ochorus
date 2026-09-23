import { getBook } from './library-public';
import { offlineBooks } from './offlineBooks.svelte';

/**
 * Download a whole Bookshelf shelf for offline — the "Download shelf" button.
 *
 * `offlineBooks` downloads one edition at a time (it refuses a second while one
 * is running), so a shelf is a QUEUE: each book not already saved, in shelf
 * order, one after another, each through the same `offlineBooks.download` the
 * book page uses (so a shelf download and a single download can't disagree on
 * what "saved offline" means). Its per-chapter progress stays on
 * `offlineBooks.active`; this adds which book of how many.
 *
 * The book detail is fetched per book — the download needs the real chapter
 * list, which the shelf's summaries don't carry.
 *
 * Stopping takes effect between books (the book in hand finishes rather than
 * leaving half its chapters cached), and the queue also stops when the device
 * goes offline. One shelf at a time: the reader's phone is the constraint this
 * is for, and parallel downloads would only compete for the same connection.
 */

export interface ShelfBookRef {
	slug: string;
	language: string;
}

export interface ShelfJob {
	shelf: string;
	total: number;
	/** Books finished so far (saved or failed). */
	done: number;
	failed: number;
	/** The book being downloaded now. */
	current: string | null;
}

/** How the last run of a shelf ended, until the next run or removal. */
export interface ShelfResult {
	saved: number;
	failed: number;
	/** Stopped early — by the reader, or by losing the connection. */
	stopped: boolean;
}

class ShelfDownload {
	job = $state<ShelfJob | null>(null);
	results = $state<Record<string, ShelfResult>>({});
	#stop = false;

	/** The shelf's books not yet saved offline. */
	missing(books: ShelfBookRef[]): ShelfBookRef[] {
		return books.filter((b) => !offlineBooks.has(b.slug, b.language));
	}

	async start(shelf: string, books: ShelfBookRef[]): Promise<void> {
		if (this.job || offlineBooks.active) return;
		const todo = this.missing(books);
		if (!todo.length) return;
		this.#stop = false;
		const { [shelf]: _previous, ...rest } = this.results;
		this.results = rest;
		this.job = { shelf, total: todo.length, done: 0, failed: 0, current: null };
		let saved = 0;
		let failed = 0;
		let stopped = false;
		for (const ref of todo) {
			if (this.#stop || !navigator.onLine) {
				stopped = true;
				break;
			}
			this.job = { ...this.job, current: ref.slug };
			let ok = false;
			try {
				const detail = await getBook(ref.slug, ref.language);
				ok = await offlineBooks.download(detail);
			} catch {
				ok = false;
			}
			// A download started elsewhere for the same edition still counts.
			if (ok || offlineBooks.has(ref.slug, ref.language)) saved += 1;
			else failed += 1;
			this.job = { ...this.job, done: saved + failed, failed, current: null };
		}
		this.job = null;
		this.results = { ...this.results, [shelf]: { saved, failed, stopped } };
	}

	/** Stop after the book in hand. */
	stop(): void {
		this.#stop = true;
	}

	/** Remove every saved download on the shelf — the storage reclaim. */
	async removeAll(shelf: string, books: ShelfBookRef[]): Promise<void> {
		if (this.job) return;
		for (const b of books) {
			if (offlineBooks.has(b.slug, b.language)) await offlineBooks.remove(b.slug, b.language);
		}
		const { [shelf]: _previous, ...rest } = this.results;
		this.results = rest;
	}
}

export const shelfDownload = new ShelfDownload();
