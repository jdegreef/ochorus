import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { readingSync } from './readingSync';
import { PLAN_SCHEDULE_KEY as KEY } from './reading-schema';
import { READING_DAYS } from './planSchedule';
import { PLAN_SCHEDULES_EVENT, type PlanSchedulePrefs } from './planScheduleRows';

export type { PlanSchedulePrefs };

/**
 * A reader's schedule choices per plan — the calendar view's start date (for a
 * plan not yet started), reading days and reminder time. localStorage is the
 * offline source of truth; when signed in, each change also mirrors to the
 * account via `readingSync`, so the choices follow the reader across devices.
 * They are choices, not a log: the newest wins (`updatedAt`, this device's
 * clock — the server compares it against the other devices'). A version bump
 * `ticks` lets Svelte views re-derive after any change, including a merge
 * writing another device's choices back.
 */

type Store = Record<string, PlanSchedulePrefs>;

const readAll = (): Store => readJSON<Store>(KEY, {});

class PlanSchedules {
	/** Bumped on every change so `$derived` consumers refresh. */
	ticks = $state(0);

	constructor() {
		// Replaced underneath us by a sign-out wipe or a merge write-back.
		if (browser) window.addEventListener('ochorus:sync', () => this.ticks++);
		// …or one plan's choice by a push that lost to a newer one (readingSync).
		if (browser) window.addEventListener(PLAN_SCHEDULES_EVENT, () => this.ticks++);
	}

	/** A plan's choices, with an unknown reading-days rule read as daily. */
	get(slug: string): PlanSchedulePrefs {
		void this.ticks;
		const p = readAll()[slug] ?? {};
		return p.rule && !READING_DAYS.includes(p.rule) ? { ...p, rule: 'daily' } : p;
	}

	/** Change some of a plan's choices, stamp them, and mirror them to the account. */
	set(slug: string, patch: Omit<PlanSchedulePrefs, 'updatedAt'>) {
		const store = readAll();
		store[slug] = { ...store[slug], ...patch, updatedAt: Date.now() };
		writeJSON(KEY, store);
		this.ticks++;
		readingSync.pushPlanSchedule(slug, store[slug]);
	}
}

export const planSchedules = new PlanSchedules();
