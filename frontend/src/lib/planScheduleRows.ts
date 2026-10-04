/**
 * A plan's calendar choices between this device and the account: both
 * directions of the mapping in one place (as shelvesData does for shelves),
 * so a field rename is one edit and the round trip is testable on its own.
 */
import type { ReadingDays } from './planSchedule';

export interface PlanSchedulePrefs {
	/** `YYYY-MM-DD` the reader chose to start on (a plan not yet started). */
	start?: string;
	rule?: ReadingDays;
	/** "HH:MM" for the calendar file's alerts. */
	time?: string;
	/** When this device made the choice (epoch ms) — newest wins across devices. */
	updatedAt?: number;
}

/** The account's row for one plan (the API's `plan_schedules`). */
export interface ServerPlanSchedule {
	plan_slug: string;
	start_on: string | null;
	reading_days: ReadingDays;
	remind_at: string;
	client_updated_at: string;
}

/** Fired when the account's choice replaces this device's outside a merge (a
 *  push that lost to a newer one): only the schedule store listens, unlike the
 *  broad 'ochorus:sync' every reading store re-reads on. */
export const PLAN_SCHEDULES_EVENT = 'ochorus:plan-schedules';

/** A plan's choices as the API takes them — the PUT body, or a merge row. */
export const scheduleToServer = (p: PlanSchedulePrefs) => ({
	start_on: p.start ?? null,
	reading_days: p.rule ?? 'daily',
	remind_at: p.time ?? '',
	updated_at: p.updatedAt
});

/** The account's row as this device keeps it. An absent start or time stays
 *  absent, so the device's own default (today, the Settings reminder) stands. */
export const scheduleFromServer = (r: ServerPlanSchedule): PlanSchedulePrefs => ({
	start: r.start_on ?? undefined,
	rule: r.reading_days,
	time: r.remind_at || undefined,
	updatedAt: Date.parse(r.client_updated_at) || 0
});
