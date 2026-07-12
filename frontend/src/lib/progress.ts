import { browser } from '$app/environment';
import { readingSync } from './readingSync';
import {
	PROGRESS_KEY,
	ANCHOR_KEY,
	chapterKey,
	type ProgressRecord,
	type ProgressMap
} from './reading-schema';

/**
 * Reading progress, stored in localStorage (keyed by book slug) as the offline
 * cache. When signed in, every change is also mirrored to the account via
 * `readingSync` so the reader's place follows them across devices.
 *
 * A record captures the exact resume point: the last `order` (chapter) opened
 * plus the `paragraph_index` scrolled to within it, so "Continue reading" can
 * deep-link straight back to the spot.
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
	if (browser) localStorage.setItem(PROGRESS_KEY, JSON.stringify(map));
}

/** All in-progress books, newest first — powers the "Continue reading" lists. */
export function allProgress(): (ProgressRecord & { slug: string })[] {
	return Object.entries(read())
		.map(([slug, r]) => ({ slug, ...r }))
		.sort((a, b) => b.at - a.at);
}

export function getProgress(slug: string): number | null {
	return read()[slug]?.order ?? null;
}

export function getProgressRecord(slug: string): ProgressRecord | null {
	return read()[slug] ?? null;
}

/** Record which chapter is open. Keeps the best-known paragraph position: the
 * device-local anchor, else (same chapter, e.g. fresh device after a sync) the
 * synced paragraph_index — so opening a chapter never clobbers the resume point
 * before the reader has restored it. */
export function saveProgress(slug: string, order: number, language = 'en'): void {
	if (!browser) return;
	const map = read();
	const prev = map[slug];
	const paragraph_index =
		getScrollAnchor(slug, order) ??
		(prev && prev.order === order ? prev.paragraph_index : 0);
	const rec: ProgressRecord = { order, paragraph_index, language, at: Date.now() };
	map[slug] = rec;
	write(map);
	readingSync.pushProgress(slug, rec);
}

/**
 * In-chapter scroll position, anchored to a paragraph index rather than a pixel
 * offset so it survives font-size / measure changes. Keyed by `slug:order`. The
 * anchor for the *current* chapter is also folded into the book's progress
 * record so a resume lands on the exact paragraph.
 */
type AnchorMap = Record<string, number>;

function readAnchors(): AnchorMap {
	if (!browser) return {};
	try {
		return JSON.parse(localStorage.getItem(ANCHOR_KEY) || '{}');
	} catch {
		return {};
	}
}

export function getScrollAnchor(slug: string, order: number): number | null {
	return readAnchors()[chapterKey(slug, order)] ?? null;
}

export function saveScrollAnchor(slug: string, order: number, paragraphIndex: number): void {
	if (!browser) return;
	const map = readAnchors();
	if (paragraphIndex <= 0) {
		delete map[chapterKey(slug, order)];
	} else {
		map[chapterKey(slug, order)] = paragraphIndex;
	}
	localStorage.setItem(ANCHOR_KEY, JSON.stringify(map));

	// Keep the book's resume point in step with where we actually are.
	const progress = read();
	const rec = progress[slug];
	if (rec && rec.order === order) {
		rec.paragraph_index = Math.max(0, paragraphIndex);
		rec.at = Date.now();
		write(progress);
		readingSync.pushProgress(slug, rec);
	}
}
