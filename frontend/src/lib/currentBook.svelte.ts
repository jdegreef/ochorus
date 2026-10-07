import { allProgress } from './progress';
import { buildResumeItems, type ResumeBook } from './resumeItems';
import { cachedResumeBooks, currentBookSlug, knownAbsent, libraryBooks } from './resumeBooks';
import type { CoverBook } from './library-public';
import { getLang } from './lang.svelte';

/**
 * The book the reader is in, resolved for the signed-in home: the hero wears
 * it as its resume point, and "Continue reading" below is told to leave it
 * out. Decided HERE, once, and handed down by HomeDashboard — two blocks each
 * working it out from storage on their own clocks could pick different books
 * mid-load and show one twice or drop it from both.
 *
 * Resolved from this build's cache of the reader's in-progress books at once
 * (so a returning reader's first paint is theirs), then from the full list
 * when it lands, and again on `ochorus:sync`. Only the one book is kept, not
 * the list: `libraryBooks` already shares the request with the strip.
 */
class CurrentBook {
	item = $state.raw<ResumeBook | null>(null);
	#generation = 0;

	/** The current book as `books` resolves it; null when they lack it. */
	#resolve(books: CoverBook[]): ResumeBook | null {
		const progress = allProgress();
		const slug = currentBookSlug(knownAbsent(getLang()), progress);
		const book = slug ? books.find((b) => b.slug === slug) : undefined;
		if (!book) return null;
		const [item] = buildResumeItems(
			[book],
			[],
			progress.filter((p) => p.kind === 'book' && p.slug === slug)
		);
		return item?.kind === 'book' ? item : null;
	}

	/** Re-resolve from the cache now and from the full list when it lands. */
	refresh() {
		const lang = getLang();
		const generation = ++this.#generation;
		if (!currentBookSlug(knownAbsent(lang))) {
			this.item = null;
			return;
		}
		// A cache that lacks the book keeps what is shown until the list says.
		this.item = this.#resolve(cachedResumeBooks(lang)) ?? this.item;
		libraryBooks(lang)
			.then((books) => {
				if (generation === this.#generation) this.item = this.#resolve(books);
			})
			.catch(() => {});
	}

	/** Follow `ochorus:sync`; returns the unsubscribe. */
	watch(): () => void {
		const refresh = () => this.refresh();
		window.addEventListener('ochorus:sync', refresh);
		return () => window.removeEventListener('ochorus:sync', refresh);
	}
}

export const currentBook = new CurrentBook();
