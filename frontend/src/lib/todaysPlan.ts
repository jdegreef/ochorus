import { planDayPath } from './editionHref';
import { getPlan, listPlans, type PlanSummary } from './library-public';
import { planProgress } from './planProgress.svelte';

/**
 * The plan day a reader is offered next: the next unread day of their most
 * recently started plan. Shared by the dashboard's "Today's reading"
 * (`TodaysReading`) and the logged-out home's "Continue reading" block
 * (`HomeResume`), so the two cannot pick different plans or days.
 */
export interface PlanToday {
	plan: PlanSummary;
	day: number;
	/** Days the reader has marked done in it. */
	done: number;
	/** False when this is an invitation to a plan, not a continuation. */
	isStarted: boolean;
	chapterTitle: string;
	bookTitle: string;
	/** The day's reading, before localisation. */
	href: string;
}

/**
 * Which plan, from this language's list: the most recently started one that
 * still has a day left, else (unless `startedOnly`) the first that has one —
 * not merely the catalog's first, which may be one the reader has finished —
 * else the first. Null when there is nothing to offer.
 */
export function pickPlan(plans: PlanSummary[], startedOnly = false): PlanSummary | null {
	const open = (p: PlanSummary) => planProgress.nextDay(p.slug, p.day_count) !== null;
	const started = planProgress
		.started()
		.map(({ slug }) => plans.find((p) => p.slug === slug))
		.find((p): p is PlanSummary => !!p && open(p));
	if (started || startedOnly) return started ?? null;
	return plans.find(open) ?? plans[0] ?? null;
}

/** Resolve the picked plan's next day (one list and one plan request). */
export async function todaysPlan(lang: string, startedOnly = false): Promise<PlanToday | null> {
	const pick = pickPlan(await listPlans(lang), startedOnly);
	if (!pick) return null;
	const next = planProgress.nextDay(pick.slug, pick.day_count);
	const detail = await getPlan(pick.slug, lang);
	// A finished plan is offered as a fresh START at day 1, never as a
	// continuation of something already complete.
	const entry = detail.days.find((d) => d.day === (next ?? 1)) ?? detail.days[0];
	if (!entry) return null;
	return {
		plan: pick,
		day: entry.day,
		done: planProgress.doneDays(pick.slug).length,
		isStarted: next !== null && planProgress.isStarted(pick.slug),
		chapterTitle: entry.chapter_title,
		bookTitle: entry.book_title,
		href: planDayPath(pick.slug, entry)
	};
}
