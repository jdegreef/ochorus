import { browser } from '$app/environment';

/**
 * Lightweight, device-local reading position for sermons.
 *
 * A sermon is a single page (no chapters), so it doesn't use the book progress
 * map — that map drives the "Continue reading" *book* lists and cross-device
 * sync, and sermons shouldn't land there. This keeps a simple slug → paragraph
 * index in its own localStorage key, so returning to a long sermon restores the
 * spot. Anchored to a paragraph index (not a pixel offset) so it survives
 * font-size / width changes, mirroring the chapter reader.
 */
const KEY = 'ochorus:sermon-anchor';

type AnchorMap = Record<string, number>;

function read(): AnchorMap {
	if (!browser) return {};
	try {
		return JSON.parse(localStorage.getItem(KEY) || '{}');
	} catch {
		return {};
	}
}

/** The saved paragraph index for a sermon (0 = start / none). */
export function getSermonAnchor(slug: string): number {
	return read()[slug] ?? 0;
}

export function saveSermonAnchor(slug: string, paragraphIndex: number): void {
	if (!browser) return;
	const map = read();
	if (paragraphIndex <= 0) delete map[slug];
	else map[slug] = paragraphIndex;
	localStorage.setItem(KEY, JSON.stringify(map));
}
