/**
 * "Continue where you left off on your other device."
 *
 * Reading position syncs to the account silently; before this, a second
 * device only learned the first had moved on at sign-in (the whole-state
 * merge). Now the reader asks for the account's position when a chapter
 * opens, and this decides whether that position is worth offering: it must
 * be NEWER than what this device knows (an older row is this device's own
 * past, or a start-over — not another device's progress) and MEANINGFULLY
 * AHEAD of where the reader is opening (a different chapter, or a good few
 * paragraphs on in the same one — never a nag over a near-identical spot).
 */

export interface Position {
	order: number;
	p: number;
	/** Client-clock ms of the device that wrote it. */
	at: number;
}

/** Same chapter: how many paragraphs ahead counts as "further along". */
export const SAME_CHAPTER_GAP = 5;

/**
 * The synced position to offer, or null.
 * @param local  this device's record before the open (null: never read here)
 * @param server the account's synced record (null: none, offline, signed out)
 * @param openedOrder the chapter being opened — the reader may have picked it
 *   by hand, so it, not the stale local record, is "where they are" when the
 *   two disagree.
 */
export function syncedAhead(
	local: Position | null,
	server: Position | null,
	openedOrder: number
): Position | null {
	if (!server) return null;
	// A record from before `at` existed (unvalidated storage) counts as ancient.
	if (local && server.at <= (Number.isFinite(local.at) ? local.at : 0)) return null;
	const here = local && local.order === openedOrder ? local : { order: openedOrder, p: 0 };
	if (server.order > here.order) return server;
	if (server.order === here.order && server.p - here.p >= SAME_CHAPTER_GAP) return server;
	return null;
}
