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

/** Reader font-size preference (A-/A+), shared across chapters. */
const SCALE_KEY = 'ochorus:reading-scale';

export function getReadingScale(): number {
	if (!browser) return 1;
	const v = parseFloat(localStorage.getItem(SCALE_KEY) || '1');
	return Number.isFinite(v) ? Math.min(1.6, Math.max(0.8, v)) : 1;
}

export function saveReadingScale(scale: number): void {
	if (browser) localStorage.setItem(SCALE_KEY, String(scale));
}
