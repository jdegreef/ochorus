import { getDailyReading, getPlan, type PlanDetail } from '$lib/library-public';
import { dateKey, isDateKey } from '$lib/dailyDate';
import { getLang } from '$lib/lang.svelte';
import { orNotFound } from '$lib/loadHelpers';
import type { PageLoad } from './$types';

// Client-only, like /today: the day shown is the reader's LOCAL date, or the
// `?d=MM-DD` they stepped to. Not prerendered (yet): one page per day per book
// per language is ~365 × 37 files — a build-time question of its own.
export const prerender = false;
export const ssr = false;

// The plan, kept across a reader's day-to-day steps — each one re-runs this
// load, and a year's plan is 366 days the chapter reader likewise fetches once.
let kept: PlanDetail | null = null;

async function planFor(slug: string, f: typeof fetch): Promise<PlanDetail | null> {
	const language = getLang();
	if (kept?.slug !== slug || kept.language !== language) {
		kept = await getPlan(slug, language, f).catch(() => null);
	}
	return kept;
}

export const load: PageLoad = async ({ params, url, fetch }) => {
	const today = dateKey(new Date());
	const asked = url.searchParams.get('d');
	const date = isDateKey(asked) ? asked : today;
	// A year-long plan's day (?plan=<slug>&day=<n>, from planDayPath): the same
	// entry, read as Day N of the plan. A plan that fails to load just leaves
	// the calendar page, rather than no page.
	const planSlug = url.searchParams.get('plan');
	const planDay = Number(url.searchParams.get('day')) || 0;
	const [reading, plan] = await Promise.all([
		// No English fallback: a language without this devotional is a 404.
		orNotFound(() => getDailyReading(params.slug, date, getLang(), fetch)),
		planSlug && planDay ? planFor(planSlug, fetch) : null
	]);
	// Only a day of that plan that reads THIS entry: a stale or edited link
	// must not tick off a day that isn't this one (as ArticleDetail guards).
	const isThisDay = plan?.days.some(
		(d) => d.day === planDay && d.book_slug === params.slug && d.entry_date === date
	);
	return isThisDay ? { reading, today, plan, planDay } : { reading, today, plan: null, planDay: 0 };
};
