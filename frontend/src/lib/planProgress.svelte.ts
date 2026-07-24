import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { readingSync } from './readingSync';
import { PLANS_KEY as KEY } from './reading-schema';

/**
 * Reading-plan progress: which plans the reader started and which days they've
 * completed. localStorage is the offline source of truth; when signed in, each
 * change also mirrors to the account via `readingSync` so plan progress follows
 * the reader across devices (roadmap #6 — books synced, plans didn't). The
 * cadence is daily and self-paced, so "done" days are the only state. A version
 * bump `ticks` lets Svelte views re-derive after any mutation.
 */

interface PlanState {
	startedAt: number;
	done: number[]; // completed day numbers
}

type Store = Record<string, PlanState>;

const readAll = (): Store => readJSON<Store>(KEY, {});

class PlanProgress {
	/** Bumped on every mutation so `$derived` consumers refresh. */
	ticks = $state(0);

	constructor() {
		// The cache can be replaced/emptied underneath us (sign-out wipe, sign-in
		// merge) — re-derive open plan views when that happens.
		if (browser) window.addEventListener('ochorus:sync', () => this.ticks++);
	}

	/** Persist the store and mirror the ONE plan that changed to the account.
	 * Every mutation goes through here, so the sync push lives in one place. */
	#write(store: Store, changed: string) {
		writeJSON(KEY, store);
		this.ticks++;
		if (store[changed]) readingSync.pushPlan(changed, store[changed]);
	}

	isStarted(slug: string): boolean {
		void this.ticks;
		return slug in readAll();
	}

	start(slug: string) {
		const store = readAll();
		if (!store[slug]) {
			store[slug] = { startedAt: Date.now(), done: [] };
			this.#write(store, slug);
		}
	}

	doneDays(slug: string): number[] {
		void this.ticks;
		return readAll()[slug]?.done ?? [];
	}

	isDone(slug: string, day: number): boolean {
		return this.doneDays(slug).includes(day);
	}

	markDone(slug: string, day: number) {
		const store = readAll();
		const state = store[slug] ?? { startedAt: Date.now(), done: [] };
		if (!state.done.includes(day)) state.done = [...state.done, day].sort((a, b) => a - b);
		store[slug] = state;
		this.#write(store, slug);
	}

	/** Un-complete a day (for the detail-page toggle). No-op if not marked. */
	unmarkDone(slug: string, day: number) {
		const store = readAll();
		const state = store[slug];
		if (!state?.done.includes(day)) return;
		state.done = state.done.filter((d) => d !== day);
		store[slug] = state;
		this.#write(store, slug);
	}

	/** Flip a day's done state; marking a day also starts the plan (via markDone). */
	toggleDone(slug: string, day: number) {
		if (this.isDone(slug, day)) this.unmarkDone(slug, day);
		else this.markDone(slug, day);
	}

	/** The next uncompleted day (1-based), or null when the plan is finished. */
	nextDay(slug: string, totalDays: number): number | null {
		const done = new Set(this.doneDays(slug));
		for (let d = 1; d <= totalDays; d++) if (!done.has(d)) return d;
		return null;
	}

	/** Started-but-unfinished plans, most recently started first. */
	started(): { slug: string; startedAt: number; doneCount: number }[] {
		void this.ticks;
		return Object.entries(readAll())
			.map(([slug, s]) => ({ slug, startedAt: s.startedAt, doneCount: s.done.length }))
			.sort((a, b) => b.startedAt - a.startedAt);
	}
}

export const planProgress = new PlanProgress();
