import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { ACTIVITY_KEY } from './reading-schema';
import { readingSync } from './readingSync';
import { localToday } from './streak';

/**
 * The reading-streak activity log: the set of local calendar days the reader
 * read on, in localStorage as an offline cache and mirrored to the account
 * (union-merged) when signed in. `recordToday()` is the one write — called from
 * `saveProgress` whenever reading advances — and is idempotent per day, so it
 * costs nothing on repeat opens the same day.
 *
 * `ticks` bumps on every change (and on the cross-store `ochorus:sync` event a
 * merge/pull dispatches) so a `$derived` streak read re-computes.
 */
class ReadingActivity {
	ticks = $state(0);

	constructor() {
		if (browser) window.addEventListener('ochorus:sync', () => (this.ticks += 1));
	}

	#load(): string[] {
		const raw = readJSON<string[]>(ACTIVITY_KEY, []);
		return Array.isArray(raw) ? raw : [];
	}

	/** All recorded days ('YYYY-MM-DD'). Reads `ticks` so callers stay reactive. */
	days(): string[] {
		this.ticks;
		return this.#load();
	}

	/** Record that reading happened today. Idempotent; pushes only a new day. */
	recordToday(): void {
		if (!browser) return;
		const today = localToday();
		const days = this.#load();
		if (days.includes(today)) return;
		days.push(today);
		writeJSON(ACTIVITY_KEY, days);
		this.ticks += 1;
		readingSync.pushActivity(today);
	}
}

export const readingActivity = new ReadingActivity();
