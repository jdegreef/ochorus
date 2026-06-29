import { browser } from '$app/environment';

/**
 * Reading progress, stored in localStorage (keyed by book slug). When login
 * lands this becomes a thin cache in front of a synced server-side record.
 */
const KEY = 'ochorus:progress';

type ProgressMap = Record<string, { order: number; at: number }>;

function read(): ProgressMap {
	if (!browser) return {};
	try {
		return JSON.parse(localStorage.getItem(KEY) || '{}');
	} catch {
		return {};
	}
}

export function getProgress(slug: string): number | null {
	return read()[slug]?.order ?? null;
}

export function saveProgress(slug: string, order: number): void {
	if (!browser) return;
	const map = read();
	map[slug] = { order, at: Date.now() };
	localStorage.setItem(KEY, JSON.stringify(map));
}

/**
 * In-chapter scroll position, anchored to a paragraph index rather than a pixel
 * offset so it survives font-size / measure changes. Keyed by `slug:order`.
 */
const ANCHOR_KEY = 'ochorus:anchors';

type AnchorMap = Record<string, number>;

function readAnchors(): AnchorMap {
	if (!browser) return {};
	try {
		return JSON.parse(localStorage.getItem(ANCHOR_KEY) || '{}');
	} catch {
		return {};
	}
}

const anchorKey = (slug: string, order: number) => `${slug}:${order}`;

export function getScrollAnchor(slug: string, order: number): number | null {
	return readAnchors()[anchorKey(slug, order)] ?? null;
}

export function saveScrollAnchor(slug: string, order: number, paragraphIndex: number): void {
	if (!browser) return;
	const map = readAnchors();
	if (paragraphIndex <= 0) {
		delete map[anchorKey(slug, order)];
	} else {
		map[anchorKey(slug, order)] = paragraphIndex;
	}
	localStorage.setItem(ANCHOR_KEY, JSON.stringify(map));
}
