import { customShelves } from './customShelves.svelte';
import { favorites } from './favorites.svelte';
import { removeWork, restoreWork } from './progress';
import { undo } from './undo.svelte';

/**
 * Moving a book between Bookshelf shelves, each one step with an Undo.
 *
 * The built-in shelves are STATES, not lists (see bookshelf.ts): a book is on
 * Reading because it has a position, on Finished because the position carries
 * a finished stamp, on To read because it's hearted and unopened. So most moves
 * are already actions of their own — Mark as finished, Move back to reading,
 * I've already read this. The one that wasn't is back to To read, which means
 * dropping the position (tombstoned on the account, so no device brings it
 * back — see progress.removeWork) and hearting the book so it lands there.
 *
 * The reader's own shelves ARE lists (customShelves), so a move between two of
 * them is taking the book off one and putting it on the other.
 */

/** Reading or Finished → To read. Moving a finished book gives up its finish
 *  (the reader asked to read it again); Undo restores position, finish and
 *  heart exactly. Returns false for a book with no position to drop. */
export function moveToToRead(slug: string): boolean {
	const wasHearted = favorites.has('book', slug);
	const rec = removeWork(slug, 'book');
	if (!rec) return false;
	if (!wasHearted) favorites.toggle('book', slug);
	undo.offer({
		kind: 'moved',
		restore: () => {
			restoreWork(slug, rec, 'book');
			if (!wasHearted && favorites.has('book', slug)) favorites.toggle('book', slug);
		}
	});
	return true;
}

/** One of the reader's shelves → another. If the book is already on the
 *  target it just leaves `from`; Undo leaves the target as it found it. */
export function moveBetweenShelves(from: string, to: string, slug: string): void {
	if (from === to) return;
	const alreadyThere = customShelves.has(to, slug);
	customShelves.setBook(from, slug, false);
	if (!alreadyThere) customShelves.setBook(to, slug, true);
	undo.offer({
		kind: 'moved',
		restore: () => {
			if (!alreadyThere) customShelves.setBook(to, slug, false);
			customShelves.setBook(from, slug, true);
		}
	});
}
