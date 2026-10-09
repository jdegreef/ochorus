import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { PLAN_TOGETHER_KEY as KEY } from './reading-schema';
import { parseIsoDay, READING_DAYS } from './planSchedule';
import { planSchedules } from './planSchedules.svelte';
import type { Together } from './planTogether';

/**
 * The "read together" groups this device has joined, by plan slug — so the
 * group's day stays on the plan page after the reader has left the link that
 * brought them. Device-only on purpose: the group is its link, and nothing
 * about who reads with whom is sent anywhere (see planTogether.ts). Joining
 * also lays the plan's own calendar on the group's dates (planSchedules), so
 * the reminders a reader sets there fall on the days the group reads.
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
		planSchedules.set(slug, { start: t.start, rule: t.rule });
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
