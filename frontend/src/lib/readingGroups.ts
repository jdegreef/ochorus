import { apiFetch } from './api';
import type { ReadingDays } from './planSchedule';
import type { Together } from './planTogether';

/**
 * "Read together" groups with totals (the API's `reading.groups`): a leader
 * turns them on for a group's link, and each reader who wants to be counted
 * chooses to be. Everything the API says about a group is a number — how
 * many have joined, how many have finished a day — and it gives no count at
 * all until `min_counted` have joined, so nobody can tell what one other
 * person did. Being counted needs an account (the count is of synced plan
 * progress); seeing the numbers doesn't.
 */
export interface GroupTotals {
	code: string;
	plan_slug: string;
	start_on: string;
	reading_days: ReadingDays;
	members: number;
	/** The day asked about, and how many members have finished it — null
	 *  below `min_counted` members. */
	day: number | null;
	done: number | null;
	min_counted: number;
	/** Whether THIS reader is counted. */
	counted: boolean;
}

/** The API's floor (`reading.groups.MIN_COUNTED`), for the leader's note
 *  before any group exists; a group's own `min_counted` is the word after. */
export const MIN_COUNTED = 5;

const url = (code: string) => `/api/reading/groups/${encodeURIComponent(code)}/`;

/** Turn on totals for a group: its code, for the link. Its leader is counted. */
export const createGroup = (plan: string, t: Together) =>
	apiFetch<GroupTotals>('/api/reading/groups/', {
		method: 'POST',
		body: JSON.stringify({ plan_slug: plan, start_on: t.start, reading_days: t.rule })
	});

/** A group's numbers, with how many have finished `day`. */
export const getGroup = (code: string, day: number | null) =>
	apiFetch<GroupTotals>(day ? `${url(code)}?day=${day}` : url(code));

/** Be counted in a group's totals. */
export const joinGroup = (code: string) => apiFetch<GroupTotals>(`${url(code)}membership/`, { method: 'PUT' });

/** Stop being counted. */
export const leaveGroup = (code: string) => apiFetch<null>(`${url(code)}membership/`, { method: 'DELETE' });
