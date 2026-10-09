import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { PLAN_TOGETHER_KEY as KEY } from './reading-schema';
import { parseIsoDay, READING_DAYS } from './planSchedule';
import type { Together } from './planTogether';

/**
 * The "read together" groups this device has joined, by plan slug — so the
 * group's day stays on the plan page after the reader has left the link that
 * brought them, and so the plan's calendar (PlanCalendar) lays the plan on the
 * group's dates. Device-only on purpose: the group is its link, and nothing
 * about who reads with whom is sent anywhere — not even to the reader's own
 * account, so joining leaves their synced schedule choices untouched.
 */

type Store = Record<string, Together>;

const readAll = (): Store => readJSON<Store>(KEY, {});

class PlanTogether {
	/** Bumped on every change so `$derived` consumers refresh. */
	ticks = $state(0);

	constructor() {
		// Emptied underneath us by the sign-out wipe.
		if (browser) window.addEventListener('ochorus:sync', () => this.ticks++);
	}

	/** The group this device joined for a plan, or null (a stored row that no
	 *  longer parses is treated as none). */
	get(slug: string): Together | null {
		void this.ticks;
		const t = readAll()[slug];
		return t && parseIsoDay(t.start) && READING_DAYS.includes(t.rule) ? t : null;
	}

	join(slug: string, t: Together) {
		const store = readAll();
		store[slug] = t;
		writeJSON(KEY, store);
		this.ticks++;
	}

	leave(slug: string) {
		const store = readAll();
		if (!(slug in store)) return;
		delete store[slug];
		writeJSON(KEY, store);
		this.ticks++;
	}
}

export const planTogether = new PlanTogether();
