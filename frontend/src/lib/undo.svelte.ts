/**
 * A single, short-lived "Undo" offer — the reader removed something (a
 * highlight, a note, a bookmark) and for a few seconds can take it back.
 *
 * One slot, not a queue: a second removal replaces the first offer, which is
 * what a person expects ("undo" means the last thing). The store knows nothing
 * about WHAT it restores — `restore` is a closure the remover builds with the
 * data it captured before deleting (see `undoable.ts`) — so it stays tiny and
 * the toast that renders it (PwaToasts) stays generic.
 *
 * The offer is let go when the thing it would restore into moves on: the marks
 * and bookmarks stores dismiss it when they load a different work or chapter,
 * and a reading-data wipe dismisses it too — an Undo must never resurrect what
 * the reader just deliberately erased.
 */

export interface UndoOffer {
	/** Put back what was removed. Must be safe to call once. */
	restore: () => void;
	/**
	 * What happened, for the wording. Default: a generic "Removed". `'note'` is a
	 * cleared note; `'finished'` is a work just marked finished (its restore
	 * un-finishes it) — the one offer that undoes an ADD rather than a removal,
	 * but the mechanism is identical: a short-lived "take it back". `'moved'` is
	 * a book moved between Bookshelf shelves (see shelfMoves).
	 */
	kind?: 'note' | 'finished' | 'moved';
	/**
	 * Show the offer INSIDE the surface that made it rather than as a corner
	 * toast. Needed when that surface is a modal dialog (the contents drawer):
	 * its focus trap and `aria-modal` put a toast outside it beyond the reach of
	 * a keyboard or a screen reader. The surface renders the offer itself and
	 * hands it back to the toast (`toToast`) when it closes.
	 */
	inline?: boolean;
}

/** How long an offer stays up before it is let go. */
export const UNDO_MS = 6000;

class Undo {
	/** The live offer, or null. Rendered by PwaToasts (or inline, see above). */
	current = $state<UndoOffer | null>(null);
	#timer: ReturnType<typeof setTimeout> | undefined;

	offer(o: UndoOffer, ms = UNDO_MS) {
		clearTimeout(this.#timer);
		this.current = o;
		this.#timer = setTimeout(() => this.dismiss(), ms);
	}

	/** Take the offer: restore, then clear. */
	act() {
		const c = this.current;
		this.dismiss();
		c?.restore();
	}

	dismiss() {
		clearTimeout(this.#timer);
		this.current = null;
	}

	/** An inline offer's surface closed: let the corner toast carry it on. */
	toToast() {
		if (this.current?.inline) this.current.inline = false;
	}
}

export const undo = new Undo();
