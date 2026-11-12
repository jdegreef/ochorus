import { allProgress } from './progress';
import { resumeBookOf, type ResumeBook } from './resumeItems';
import { cachedResumeBooks, currentBookSlug, knownAbsent, libraryBooks } from './resumeBooks';
import { workSlugKey } from './reading-schema';
import { getLang } from './lang.svelte';

/**
 * The book the reader is in, resolved for the signed-in home: the hero wears
 * it as its resume point, and "Continue reading" below is told to leave it
 * out. Decided HERE, once, and handed down by HomeDashboard — two blocks each
 * working it out from storage on their own clocks could pick different books
 * mid-load and show one twice or drop it from both.
 *
 * Two answers, on two clocks. `key` — WHICH book — is known at once from
 * progress, so the strip never reserves a card it would then drop. `item` —
 * the book itself, for the hero to draw — comes from this build's cache of
 * the reader's in-progress books when it has it (so a returning reader's
 * first paint is theirs), else from the full list when it lands. Followed on
 * `ochorus:sync`. Only the one book is kept, not the list: `libraryBooks`
 * already shares the request with the strip.
 */
class CurrentBook {
	item = $state.raw<ResumeBook | null>(null);
	key = $state<string | undefined>(undefined);
	/** The full list is still on its way, so a null `item` may yet come. Once
	 * false, a key with no item is a book that cannot be drawn (the list
	 * failed), and the logged-out home keeps its hero (HomeMarketing). */
	pending = $state(false);
	#generation = 0;
	#lang = '';

	/** Re-resolve from the cache now and from the full list when it lands. */
	refresh() {
		const lang = getLang();
		const generation = ++this.#generation;
		const progress = allProgress();
		const slug = currentBookSlug(knownAbsent(lang), progress);
		this.key = slug ? workSlugKey('book', slug) : undefined;
		// What is shown stays only while it is still the current book, in this
		// language: a cache that lacks the book then leaves it to the list.
		const kept = this.#lang === lang && this.item?.slug === slug ? this.item : null;
		this.#lang = lang;
		if (!slug) {
			this.item = null;
			this.pending = false;
			return;
		}
		this.item = resumeBookOf(cachedResumeBooks(lang), slug, progress) ?? kept;
		this.pending = true;
		libraryBooks(lang)
			.then((books) => {
				if (generation !== this.#generation) return;
				// The list has marked what this language lacks: ask again.
				const now = currentBookSlug(knownAbsent(lang));
				this.key = now ? workSlugKey('book', now) : undefined;
				this.item = now ? resumeBookOf(books, now) : null;
			})
			.catch(() => {})
			.finally(() => {
				if (generation === this.#generation) this.pending = false;
			});
	}

	/** Follow `ochorus:sync`; returns the unsubscribe. */
	watch(): () => void {
		const refresh = () => this.refresh();
		window.addEventListener('ochorus:sync', refresh);
		return () => window.removeEventListener('ochorus:sync', refresh);
	}
}

export const currentBook = new CurrentBook();
