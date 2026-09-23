import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';

/**
 * The reader's weekly reading goal — "read on N days a week" (1–7). A device
 * *preference* (like theme or font size), not reading data: it's a personal
 * target, so it lives in its own localStorage key and is NOT wiped on sign-out
 * (it isn't in READING_DATA_KEYS). Progress toward it is computed from the
 * synced activity log via heatmap.weekReadCount — the goal itself is just the
 * target number.
 */

const KEY = 'ochorus:reading-goal';
/** The yearly books goal, per year: `{ "2026": 12 }`. Same footing as the
 *  weekly goal — a personal target kept on this device, not reading data. */
const BOOKS_KEY = 'ochorus:reading-goal-books';
export const BOOKS_GOAL_MIN = 1;
export const BOOKS_GOAL_MAX = 365;
export const GOAL_MIN = 1;
export const GOAL_MAX = 7;
export const DEFAULT_GOAL = 4;

function clamp(n: unknown): number {
	const x = Math.round(Number(n));
	if (!Number.isFinite(x)) return DEFAULT_GOAL;
	return Math.min(GOAL_MAX, Math.max(GOAL_MIN, x));
}

class ReadingGoal {
	/** Target days per week. Read reactively; change only via `set`. */
	perWeek = $state(DEFAULT_GOAL);

	constructor() {
		if (browser) this.perWeek = clamp(readJSON<number>(KEY, DEFAULT_GOAL));
	}

	set(n: number): void {
		this.perWeek = clamp(n);
		if (browser) writeJSON(KEY, this.perWeek);
	}

	/** Books-per-year goals, keyed by year. Read via `booksFor`. */
	books = $state<Record<string, number>>(browser ? readBooks() : {});

	/** The goal for `year`, or null when none is set. */
	booksFor(year: number): number | null {
		return this.books[String(year)] ?? null;
	}

	/** Set (clamped to 1–365) or clear (`null`) the goal for `year`. */
	setBooks(year: number, n: number | null): void {
		const next = { ...this.books };
		const x = Math.round(Number(n));
		if (n === null || !Number.isFinite(x)) delete next[String(year)];
		else next[String(year)] = Math.min(BOOKS_GOAL_MAX, Math.max(BOOKS_GOAL_MIN, x));
		this.books = next;
		if (browser) writeJSON(BOOKS_KEY, next);
	}
}

/** Stored yearly goals, dropping anything that isn't a whole number in range. */
function readBooks(): Record<string, number> {
	const raw = readJSON<Record<string, unknown>>(BOOKS_KEY, {});
	const out: Record<string, number> = {};
	if (raw && typeof raw === 'object') {
		for (const [year, n] of Object.entries(raw)) {
			if (/^\d{4}$/.test(year) && Number.isInteger(n) && (n as number) >= BOOKS_GOAL_MIN && (n as number) <= BOOKS_GOAL_MAX) {
				out[year] = n as number;
			}
		}
	}
	return out;
}

export const readingGoal = new ReadingGoal();
