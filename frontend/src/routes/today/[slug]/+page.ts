import { getDailyReading } from '$lib/library-public';
import { dateKey, isDateKey } from '$lib/dailyDate';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { PageLoad } from './$types';

// Client-only, like /today: the day shown is the reader's LOCAL date, or the
// `?d=MM-DD` they stepped to. Not prerendered (yet): one page per day per book
// per language is ~365 × 37 files — a build-time question of its own.
export const prerender = false;
export const ssr = false;

export const load: PageLoad = async ({ params, url, fetch }) => {
	const today = dateKey(new Date());
	const asked = url.searchParams.get('d');
	const date = isDateKey(asked) ? asked : today;
	// No English fallback: a language without this devotional is a 404.
	const reading = await orNotFound(() => getDailyReading(params.slug, date, getLang(), fetch));
	return { reading, today };
};
