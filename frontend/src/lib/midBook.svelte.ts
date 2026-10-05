/**
 * "You're reading chapter 14 of All of Grace": a small welcome for a reader
 * who arrives in the middle of a book with no place in it yet — almost always
 * from search, which lands on chapter pages more than anywhere else (46% of
 * search clicks, Search Console, 2026-09). It offers the beginning, the
 * book's page, and a Save. Shown in the bottom stack (PwaToasts), so the
 * chapter text never moves under the reader.
 *
 * The reader page decides WHEN (a first open of this book, past chapter 1,
 * not a plan day or a deliberate jump); this holds what to show. Dismissed
 * per book for the session, and gone once the reader scrolls on into the text.
 */
export interface MidBookWelcome {
	slug: string;
	bookTitle: string;
	author: string;
	order: number;
	/** Chapter 1 and the book page, already localized. */
	firstHref: string;
	bookHref: string;
}

class MidBook {
	current = $state<MidBookWelcome | null>(null);
	#dismissed = new Set<string>();

	show(w: MidBookWelcome) {
		if (this.#dismissed.has(w.slug)) return;
		this.current = w;
	}

	dismiss() {
		if (this.current) this.#dismissed.add(this.current.slug);
		this.current = null;
	}

	/** Navigation away, or the reader settled in: let it go quietly. */
	clear() {
		this.current = null;
	}
}

export const midBook = new MidBook();
