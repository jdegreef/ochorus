import { readJSON, writeJSON } from './persisted';
import { planSchedules } from './planSchedules.svelte';
import { readReminderTime } from './reminder';
import { signInSheet } from './signInSheet.svelte';
import type { SignupSource } from './signupSource';

/**
 * Turning on a plan's daily reminder email, wherever it's offered: the sheet
 * shown when a plan starts (PlanStartSheet), the end of a plan day
 * (PlanDayRemind signed in, ChapterEndAsk signed out) and the plan's calendar
 * view. The email is sent by the account (emails.plan_reminders) from the
 * plan's synced schedule, so a signed-out reader is asked for an account
 * first and the choice is HELD until one exists.
 *
 * One place applies a held choice: `applyHeldPlanEmail`, which the root
 * layout runs whenever a reader is signed in. So it doesn't matter how the
 * account arrives: the sign-up panel, "Sign in" from it to /login, Google's
 * round trip, or a confirmation link opened later. A choice is held for 15
 * minutes: long enough to confirm an email or find a password, short enough
 * that signing in later for some other reason (or someone else signing in on
 * a shared browser) doesn't switch on email nobody remembers asking for.
 */

const HELD_KEY = 'ochorus:plan-email-held';
export const HOLD_MS = 15 * 60 * 1000;

/**
 * The time a plan's email would go out: the plan's own, else the reader's
 * reminder time from Settings, as the plan's calendar view shows it.
 */
export function planRemindTime(slug: string): string {
	return planSchedules.get(slug).time || readReminderTime();
}

/** Save the opt-in on the plan's schedule (synced up to the account). */
export function turnOnPlanEmail(slug: string, time?: string): void {
	// Only the two fields: set() merges, and re-writing the rest via get()
	// would store its normalized `rule` over a newer device's choice.
	planSchedules.set(slug, { time: time || planRemindTime(slug), email: true });
}

/** And off, for this plan alone. */
export function turnOffPlanEmail(slug: string): void {
	planSchedules.set(slug, { email: false });
}

/**
 * A signed-out reader asked for `slug`'s email: hold the choice and open the
 * sign-up panel, credited to `source`. (Signed in, call turnOnPlanEmail.)
 */
export function askForPlanEmail(slug: string, source: SignupSource, time?: string): void {
	writeJSON(HELD_KEY, { slug, time: time || planRemindTime(slug), at: Date.now() });
	signInSheet.show(source);
}

/**
 * Turn on a held choice, if one is fresh, and drop it either way. Returns the
 * plan it was for, or null. Called by the root layout once signed in.
 */
export function applyHeldPlanEmail(now = Date.now()): string | null {
	const held = readJSON<{ slug?: unknown; time?: unknown; at?: unknown } | null>(HELD_KEY, null);
	if (!held) return null;
	writeJSON(HELD_KEY, null);
	if (typeof held.slug !== 'string' || typeof held.at !== 'number') return null;
	if (now < held.at || now - held.at > HOLD_MS) return null;
	turnOnPlanEmail(held.slug, typeof held.time === 'string' ? held.time : undefined);
	return held.slug;
}

// "Not now" on the signed-in plan-day card: that plan stops offering it (its
// calendar view still has the switch). Per plan, so a new plan asks again.
const DECLINED_KEY = 'ochorus:plan-email-declined';

export function planEmailDeclined(slug: string): boolean {
	const list = readJSON<unknown>(DECLINED_KEY, []);
	return Array.isArray(list) && list.includes(slug);
}

export function declinePlanEmail(slug: string): void {
	const list = readJSON<unknown>(DECLINED_KEY, []);
	const slugs = Array.isArray(list) ? list.filter((s): s is string => typeof s === 'string') : [];
	if (!slugs.includes(slug)) writeJSON(DECLINED_KEY, [...slugs, slug].slice(-50));
}
