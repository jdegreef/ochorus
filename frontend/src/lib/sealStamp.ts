import { readJSON, writeJSON } from './persisted';

/**
 * Which seals this device has already watched being pressed. A seal stamps
 * down into the wax once — the first time the finish panel shows it — and
 * after that it simply sits there: reopening a finished book's last page is a
 * look back, not a second arrival. Device-only and cosmetic; a lost entry only
 * means one more stamp, so it is not synced and not wiped with reading data.
 */
export const SEAL_STAMPED_KEY = 'ochorus:seals-stamped';

/** The keys in `keys` not yet in `stamped`, in their given order. */
export function freshSeals(keys: string[], stamped: string[]): string[] {
	const seen = new Set(stamped);
	return keys.filter((k) => !seen.has(k));
}

/**
 * Mark `keys` as stamped and return the ones that are new to this device —
 * the seals the caller should animate now. Recording before the animation
 * runs means a second panel (another tab, a re-render) never stamps twice.
 */
export function claimStamps(keys: string[]): Set<string> {
	const saved = readJSON<unknown>(SEAL_STAMPED_KEY, []);
	const stamped = Array.isArray(saved) ? (saved as string[]) : [];
	const fresh = freshSeals(keys, stamped);
	if (fresh.length) writeJSON(SEAL_STAMPED_KEY, [...stamped, ...fresh]);
	return new Set(fresh);
}
