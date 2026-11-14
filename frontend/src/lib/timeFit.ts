/**
 * "How long do you have?" — the /today page's time picker (`TimePicker`).
 *
 * Pure parts, tested beside it: the choices, the word window a choice means at
 * the reader's pace, the reading places sent to the API, and the remembered
 * choice. The selection itself is the API's (`/api/library/fit/`).
 */
import type { ProgressRecord, WorkKind } from './reading-schema';
import { isFinishedNow, resumeOrderOf } from './reading-schema';

/** The choices, in minutes. */
export const TIME_CHOICES = [5, 15, 30, 60] as const;
export type TimeChoice = (typeof TIME_CHOICES)[number];
export const DEFAULT_TIME: TimeChoice = 15;

/** A device preference, not reading data: which time the picker last showed. */
export const TIME_KEY = 'ochorus:time-picker';

/**
 * The words that fit `minutes` at `wpm`: no more than the time there is, and
 * at least half of it, so "an hour" does not offer a two-minute read. The API
 * falls back to the longest work under the top when the window is empty.
 */
export function wordWindow(minutes: number, wpm: number): { min: number; max: number } {
	const max = Math.max(1, Math.round(minutes * wpm));
	return { min: Math.round(max / 2), max };
}

/**
 * The books the reader is in the middle of, in this language, newest first,
 * as the API's `reading` parameter: `slug:order` pairs, the order the one
 * "Continue" would open. Finished books, sermons and other kinds drop out.
 */
export function readingPlaces(
	progress: (ProgressRecord & { slug: string; kind: WorkKind })[],
	language: string,
	limit = 3
): string {
	return progress
		.filter((p) => p.kind === 'book' && !isFinishedNow(p) && p.language === language)
		.slice(0, limit)
		.map((p) => `${p.slug}:${resumeOrderOf(p)}`)
		.join(',');
}

/** The stored choice, or the default for anything else (unset, stale, junk). */
export function parseTime(raw: string | null): TimeChoice {
	const n = Number(raw);
	return (TIME_CHOICES as readonly number[]).includes(n) ? (n as TimeChoice) : DEFAULT_TIME;
}

/** Days since the epoch on the reader's own calendar — the API's `seed`, so
 *  the picks hold all day and change tomorrow. */
export function daySeed(now: Date): number {
	return Math.floor(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86_400_000);
}
