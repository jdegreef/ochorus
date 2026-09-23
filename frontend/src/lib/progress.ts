import { browser } from '$app/environment';
import { readingSync } from './readingSync';
import { readingActivity } from './readingActivity.svelte';
import { storageHealth } from './storageHealth.svelte';
import { undo, UNDO_MS } from './undo.svelte';
import { addPending, clearPending } from './removals';
import {
	PROGRESS_KEY,
	ANCHOR_KEY,
	migrateLegacySermonState,
	workKey,
	workSlugKey,
	parseWorkSlugKey,
	type WorkKind,
	type ProgressRecord,
	type ProgressMap
} from './reading-schema';

/** Guarded localStorage write: never throws (a quota error here runs inside the
 * reader's per-chapter effect), and flags storageHealth so the reader is warned
 * their place/notes may not persist rather than losing them silently. */
function safeSet(key: string, value: string): void {
	try {
		localStorage.setItem(key, value);
	} catch {
		storageHealth.fail();
	}
}

/**
 * Reading progress, stored in localStorage (keyed by work — bare slug for
 * books, `sermon:slug` for sermons) as the offline cache. When signed in,
 * every change is also mirrored to the account via `readingSync` so the
 * reader's place follows them across devices.
 *
 * A record captures the exact resume point: the last `order` (chapter) opened
 * plus the `paragraph_index` scrolled to within it (sermons are single
 * documents — their order is always 1), so "Continue reading" can deep-link
 * straight back to the spot.
 */
function read(): ProgressMap {
	if (!browser) return {};
	try {
		return JSON.parse(localStorage.getItem(PROGRESS_KEY) || '{}');
	} catch {
		return {};
	}
}

function write(map: ProgressMap) {
	if (browser) safeSet(PROGRESS_KEY, JSON.stringify(map));
}

/** All in-progress works, newest first — powers the "Continue reading" lists. */
export function allProgress(): (ProgressRecord & { slug: string; kind: WorkKind })[] {
	return Object.entries(read())
		.map(([key, r]) => ({ ...parseWorkSlugKey(key), ...r }))
		.sort((a, b) => b.at - a.at);
}

export function getProgress(slug: string, kind: WorkKind = 'book'): number | null {
	return read()[workSlugKey(kind, slug)]?.order ?? null;
}

export function getProgressRecord(slug: string, kind: WorkKind = 'book'): ProgressRecord | null {
	return read()[workSlugKey(kind, slug)] ?? null;
}

/** Record which chapter is open. Keeps the best-known paragraph position: the
 * device-local anchor, else (same chapter, e.g. fresh device after a sync) the
 * synced paragraph_index — so opening a chapter never clobbers the resume point
 * before the reader has restored it. */
export function saveProgress(
	slug: string,
	order: number,
	language = 'en',
	kind: WorkKind = 'book'
): void {
	if (!browser) return;
	const map = read();
	const key = workSlugKey(kind, slug);
	const prev = map[key];
	const paragraph_index =
		getScrollAnchor(slug, order, kind) ??
		(prev && prev.order === order ? prev.paragraph_index : 0);
	// `at` is when the POSITION last changed, not when the book was last
	// opened. A bare open of the same spot used to re-stamp it "now", which
	// made this device's untouched place look newer than another device's real
	// reading — and, pushed on sign-in, overwrote it on the server. The record
	// is left alone until the reader actually moves.
	if (prev && prev.order === order && prev.paragraph_index === paragraph_index && prev.language === language) {
		readingActivity.recordToday();
		return;
	}
	// Carry a finished stamp forward: reopening a finished work and reading on
	// does not un-finish it (only an explicit un-finish clears it).
	const rec: ProgressRecord = {
		order,
		paragraph_index,
		language,
		at: Date.now(),
		finished_at: prev?.finished_at ?? null
	};
	map[key] = rec;
	write(map);
	readingSync.pushProgress(kind, slug, rec);
	// Opening/advancing a chapter is the "read today" signal for the streak.
	readingActivity.recordToday();
}

/** Has the reader finished this work? */
export function isFinished(slug: string, kind: WorkKind = 'book'): boolean {
	return getProgressRecord(slug, kind)?.finished_at != null;
}

/**
 * Mark a work finished — reaching the end of the last chapter / single document,
 * or an explicit tap. Idempotent: already-finished is a no-op, so the readers
 * can call it freely on every scroll-to-the-end without re-pushing. Requires an
 * existing progress record (there always is one — the reader saves a position on
 * open before anything can finish); a work with no position can't be finished.
 * Returns true when it flipped a work to finished (so a caller can offer Undo).
 */
export function markFinished(slug: string, kind: WorkKind = 'book'): boolean {
	if (!browser) return false;
	const map = read();
	const key = workSlugKey(kind, slug);
	const rec = map[key];
	if (!rec || rec.finished_at != null) return false;
	rec.finished_at = Date.now();
	write(map);
	// Not debounced: a discrete action, and coalescing it with scroll saves is a
	// hazard for the un-finish direction (see readingSync.setFinished).
	readingSync.setFinished(kind, slug, rec, true);
	window.dispatchEvent(new CustomEvent('ochorus:sync'));
	return true;
}

/**
 * Mark finished AND offer a short Undo — the one "I'm done with this" action
 * behind both auto-detection (reaching the end in a reader) and the explicit
 * taps (the dashboard card). Silent when the work is already finished
 * (`markFinished` is a no-op, so no misleading Undo appears).
 */
export function offerFinish(slug: string, kind: WorkKind = 'book'): void {
	if (markFinished(slug, kind)) {
		undo.offer({ restore: () => unmarkFinished(slug, kind), kind: 'finished' });
	}
}

/**
 * "I've already read this" — finish a book the reader never opened on this
 * device (read on paper, or before Ochorus), straight from the Bookshelf's To
 * read shelf. It gets a record at its last chapter, stamped finished, and a
 * short Undo like any other finish.
 *
 * The account only hears about it once the Undo has lapsed. The server can
 * clear a finish but never forget a position, so pushing at once would make an
 * Undo leave the book on the Reading shelf at its last chapter, not back where
 * it was. Held back, an Undo simply deletes the local record and there is
 * nothing to forget. (A tab closed inside those few seconds leaves the finish
 * local-only until the next sign-in merge carries it up.)
 *
 * A work that already has a record goes through the ordinary `offerFinish`.
 */
export function offerFinishUnopened(
	slug: string,
	lastOrder: number,
	language: string,
	kind: WorkKind = 'book'
): void {
	if (!browser) return;
	const map = read();
	const key = workSlugKey(kind, slug);
	if (map[key]) {
		offerFinish(slug, kind);
		return;
	}
	const now = Date.now();
	const rec: ProgressRecord = {
		order: Math.max(1, lastOrder),
		paragraph_index: 0,
		language,
		at: now,
		finished_at: now
	};
	map[key] = rec;
	write(map);
	window.dispatchEvent(new CustomEvent('ochorus:sync'));
	const push = setTimeout(() => readingSync.setFinished(kind, slug, rec, true), UNDO_MS);
	undo.offer({
		kind: 'finished',
		restore: () => {
			clearTimeout(push);
			const m = read();
			delete m[key];
			write(m);
			window.dispatchEvent(new CustomEvent('ochorus:sync'));
		}
	});
}

/**
 * Take a work off the reader's shelf — the Bookshelf's "Remove from shelf" for
 * a book being read or finished. Drops its position here and on the account,
 * which keeps a tombstone so another device still holding the position can't
 * merge it back (reading.models.Removal). Until the account confirms, the
 * removal waits in removals.ts and rides the next merge.
 *
 * Highlights, notes, bookmarks and the reading streak are untouched: this
 * removes the book from the shelf, not the reading that happened in it.
 * Returns the removed record, for `restoreWork` (Undo).
 */
export function removeWork(slug: string, kind: WorkKind = 'book'): ProgressRecord | null {
	if (!browser) return null;
	const map = read();
	const key = workSlugKey(kind, slug);
	const rec = map[key];
	if (!rec) return null;
	delete map[key];
	write(map);
	const at = addPending('progress', kind, slug);
	readingSync.removeProgress(kind, slug, at);
	window.dispatchEvent(new CustomEvent('ochorus:sync'));
	return rec;
}

/**
 * Undo `removeWork`: put the record back, stamped NOW. The account may already
 * hold the tombstone, and it only yields to a write newer than the removal —
 * so the restored position is re-pushed with a fresh clock (its chapter,
 * paragraph and any finish carried unchanged), which lifts the tombstone.
 */
export function restoreWork(slug: string, rec: ProgressRecord, kind: WorkKind = 'book'): void {
	if (!browser) return;
	clearPending('progress', kind, slug);
	const map = read();
	const restored: ProgressRecord = { ...rec, at: Date.now() };
	map[workSlugKey(kind, slug)] = restored;
	write(map);
	readingSync.pushProgress(kind, slug, restored);
	window.dispatchEvent(new CustomEvent('ochorus:sync'));
}

/** Un-finish a work — an explicit "not done after all" / Undo. Clears the stamp
 *  and, while online, tells the server to clear it too (a live-only signal, like
 *  un-favoriting; the sign-in merge never carries it). */
export function unmarkFinished(slug: string, kind: WorkKind = 'book'): void {
	if (!browser) return;
	const map = read();
	const key = workSlugKey(kind, slug);
	const rec = map[key];
	if (!rec || rec.finished_at == null) return;
	rec.finished_at = null;
	write(map);
	readingSync.setFinished(kind, slug, rec, false);
	window.dispatchEvent(new CustomEvent('ochorus:sync'));
}

/**
 * The account's synced position in a work — what another device last pushed —
 * or null when there is none, or the reader is offline or signed out. The
 * route-facing name for `readingSync.fetchProgress`, so surfaces keep going
 * through this module for everything progress-shaped.
 */
export function fetchSyncedProgress(slug: string, kind: WorkKind = 'book'): Promise<ProgressRecord | null> {
	return readingSync.fetchProgress(kind, slug);
}

/**
 * In-chapter scroll position, anchored to a paragraph index rather than a pixel
 * offset so it survives font-size / measure changes. Keyed by `slug:order`
 * (books) / `sermon:slug:1` (sermons). The anchor for the *current* chapter is
 * also folded into the work's progress record so a resume lands on the exact
 * paragraph.
 */
type AnchorMap = Record<string, number>;

function readAnchors(): AnchorMap {
	if (!browser) return {};
	migrateLegacySermonState();
	try {
		return JSON.parse(localStorage.getItem(ANCHOR_KEY) || '{}');
	} catch {
		return {};
	}
}

export function getScrollAnchor(
	slug: string,
	order: number,
	kind: WorkKind = 'book'
): number | null {
	return readAnchors()[workKey(kind, slug, order)] ?? null;
}

export function saveScrollAnchor(
	slug: string,
	order: number,
	paragraphIndex: number,
	kind: WorkKind = 'book'
): void {
	if (!browser) return;
	const map = readAnchors();
	if (paragraphIndex <= 0) {
		delete map[workKey(kind, slug, order)];
	} else {
		map[workKey(kind, slug, order)] = paragraphIndex;
	}
	safeSet(ANCHOR_KEY, JSON.stringify(map));

	// Keep the work's resume point in step with where we actually are — when
	// it moved. A restore lands on the paragraph the record already names and
	// fires the same save; that is not reading, and must not re-stamp `at`
	// (see saveProgress).
	const progress = read();
	const rec = progress[workSlugKey(kind, slug)];
	const p = Math.max(0, paragraphIndex);
	if (rec && rec.order === order && rec.paragraph_index !== p) {
		rec.paragraph_index = p;
		rec.at = Date.now();
		write(progress);
		readingSync.pushProgress(kind, slug, rec);
	}
}
