import { planProgress } from './planProgress.svelte';
import type { PlanSummary } from './library-public';

/**
 * One reading-plan the reader has started, resolved against the current-language
 * plan catalog for its title and day count — the shape both the home "Your
 * plans" overview and the /reading page render through `PlanCard`, so the two
 * can't drift on what a plan card looks like or on what counts as finished.
 *
 * A plan is finished when the reader has completed every day — the same
 * "no next uncompleted day" rule the plan detail page uses. Progress is
 * device-local (`planProgress`); a started plan with no catalog row in the
 * current language is dropped rather than shown as a bare slug.
 */
export interface PlanRow {
	slug: string;
	title: string;
	/** Total days in the plan. */
	total: number;
	/** Days the reader has completed. */
	done: number;
	/** Completion percent, 0–100. */
	pct: number;
	/** No next uncompleted day left — the split "In progress" vs "Finished". */
	finished: boolean;
}

/**
 * Resolve the reader's started plans into progress rows, newest-started first
 * (`planProgress.started()` already sorts). `plans` is the current-language plan
 * catalog the caller already has. Reads `planProgress.ticks` so a Svelte
 * `$derived`/`$effect` calling this refreshes on any plan-progress change.
 */
export function buildPlanRows(plans: PlanSummary[]): PlanRow[] {
	void planProgress.ticks;
	const bySlug = new Map(plans.map((p) => [p.slug, p]));
	return planProgress
		.started()
		.map(({ slug }) => bySlug.get(slug))
		.filter((p): p is PlanSummary => !!p)
		.map((p) => {
			const done = planProgress.doneDays(p.slug).length;
			const total = p.day_count;
			return {
				slug: p.slug,
				title: p.title,
				total,
				done,
				pct: total ? Math.round((done / total) * 100) : 0,
				finished: planProgress.nextDay(p.slug, total) === null
			};
		});
}
