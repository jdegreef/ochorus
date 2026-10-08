import { readJSON, writeJSON } from './persisted';

/**
 * When the end-of-chapter "Keep your place" card may show to a signed-out
 * reader (ChapterEndAsk): from the end of the first chapter they finish on
 * this device, wherever they started. A search visitor landing on chapter 7
 * who reads to its end has just shown the most intent they will, and about
 * half of search visitors land mid-book, so waiting for a second chapter end
 * lost most of them. Only an end actually reached counts (the card's
 * IntersectionObserver), not a page opened. "Not now" hides it for a week;
 * after three of those it stays away.
 */
const KEY = 'ochorus:chapter_ask';
const ENDS_KEY = 'ochorus:chapter_ends';
/** Chapter ends needed before the card shows. */
export const ENDS_BEFORE_ASK = 1;
/** Only "at least one" matters, so a short list is plenty. */
const ENDS_KEPT = 5;
export const SNOOZE_MS = 7 * 24 * 60 * 60 * 1000;
export const MAX_DISMISSALS = 3;

interface AskState {
	until: number;
	dismissals: number;
}

function read(): AskState {
	const s = readJSON<Partial<AskState> | null>(KEY, null);
	return {
		until: typeof s?.until === 'number' ? s.until : 0,
		dismissals: typeof s?.dismissals === 'number' ? s.dismissals : 0
	};
}

/**
 * Note that the reader reached the end of chapter `key` (e.g. "book:humility:3")
 * and return how many distinct chapter ends this device has seen (capped).
 */
export function noteChapterEnd(key: string): number {
	const ends = readJSON<string[]>(ENDS_KEY, []);
	const list = Array.isArray(ends) ? ends.filter((k) => typeof k === 'string') : [];
	if (!list.includes(key)) {
		list.push(key);
		writeJSON(ENDS_KEY, list.slice(-ENDS_KEPT));
	}
	return Math.min(list.length, ENDS_KEPT);
}

/** @param endsReached distinct chapter ends reached on this device */
export function shouldAsk(endsReached: number, now = Date.now()): boolean {
	if (endsReached < ENDS_BEFORE_ASK) return false;
	const s = read();
	return s.dismissals < MAX_DISMISSALS && now >= s.until;
}

export function snoozeAsk(now = Date.now()): void {
	const s = read();
	writeJSON(KEY, { until: now + SNOOZE_MS, dismissals: s.dismissals + 1 });
}
