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
}

export const readingGoal = new ReadingGoal();
