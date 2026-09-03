import { marks, type Mark } from './marks.svelte';
import { bookmarks } from './bookmarks.svelte';
import { undo } from './undo.svelte';

/**
 * Undoable removals. Each captures what a restore needs BEFORE deleting, then
 * offers the reader a few seconds to take it back. The stores themselves stay
 * pure (remove is remove); the undo semantics live here, at the user-action
 * boundary, so sync and other internal callers are unaffected.
 *
 * Every restore is guarded on the store still being on the same work/chapter
 * it was captured from. The stores dismiss the offer when they move on, so
 * the guard is belt-and-braces: a reader who navigates and then taps Undo
 * must not get the old chapter's mark written into the new one.
 */

/** Remove a highlight group; Undo puts back the very segments that were there. */
export function removeMarkUndoable(id: string) {
	const key = marks.key;
	// Plain copies of the whole segments — note, colour AND edition tag — so the
	// restore is lossless: an untagged legacy mark comes back untagged (visible
	// in every edition, as before), not re-stamped with the current one.
	const group: Mark[] = marks.list.filter((m) => m.id === id).map((m) => ({ ...m }));
	if (!group.length) return;
	marks.remove(id);
	undo.offer({
		restore: () => {
			if (marks.key === key) marks.restore(group);
		}
	});
}

/** Clear a highlight's note; Undo puts the text back. A no-note clear does nothing. */
export function clearNoteUndoable(id: string) {
	const key = marks.key;
	const old = marks.getNote(id);
	if (!old) return;
	marks.setNote(id, '');
	undo.offer({
		kind: 'note',
		restore: () => {
			if (marks.key === key) marks.setNote(id, old);
		}
	});
}

/** Remove a bookmark; Undo re-saves the same spot with its cached text. */
export function removeBookmarkUndoable(id: string, opts: { inline?: boolean } = {}) {
	const key = bookmarks.key;
	const bm = bookmarks.list.find((b) => b.id === id);
	if (!bm) return;
	const { order, p, snippet, title } = bm;
	bookmarks.remove(id);
	undo.offer({
		...opts,
		restore: () => {
			if (bookmarks.key === key && !bookmarks.has(order, p)) {
				bookmarks.toggle(order, p, snippet, title);
			}
		}
	});
}
