import { browser } from '$app/environment';
import { readingSync } from './readingSync';
import { storageHealth } from './storageHealth.svelte';
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
	const rec: ProgressRecord = { order, paragraph_index, language, at: Date.now() };
	map[key] = rec;
	write(map);
	readingSync.pushProgress(kind, slug, rec);
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

	// Keep the work's resume point in step with where we actually are.
	const progress = read();
	const rec = progress[workSlugKey(kind, slug)];
	if (rec && rec.order === order) {
		rec.paragraph_index = Math.max(0, paragraphIndex);
		rec.at = Date.now();
		write(progress);
		readingSync.pushProgress(kind, slug, rec);
	}
}
