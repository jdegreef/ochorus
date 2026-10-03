// The retention grid's derived numbers: each column's share across every
// cohort that reached it, and the week-4 headline comparing newer cohorts
// with older ones. Pure, so the page stays markup and these stay tested.

import type { EngagementCohort } from './library-admin';

export type Share = { readers: number; people: number; pct: number };

export const share = (readers: number, people: number): Share => ({
	readers,
	people,
	pct: people ? Math.round((readers / people) * 100) : 0
});

/** Each week-after column across the shown cohorts that reached it, weighted
 *  by size (a cohort of 20 counts for more than one of 5). Null where no
 *  shown cohort has reached that week yet. */
export function columnShares(rows: EngagementCohort[], span: number): (Share | null)[] {
	return Array.from({ length: span }, (_, k) => {
		const reached = rows.filter((r) => r.active && r.active.length > k);
		if (!reached.length) return null;
		return share(
			reached.reduce((a, r) => a + r.active![k], 0),
			reached.reduce((a, r) => a + r.size, 0)
		);
	});
}

/** The week that decides retention for slow reads. */
export const HEADLINE_WEEK = 4;

/** Week-4 retention for the newer half of the cohorts that have reached it,
 *  against the older half, with each half's join weeks. Null until two
 *  cohorts have reached it. */
export function headline(rows: EngagementCohort[]) {
	const reached = rows.filter((r) => r.active && r.active.length > HEADLINE_WEEK);
	if (reached.length < 2) return null;
	const half = Math.floor(reached.length / 2);
	const part = (group: EngagementCohort[]) => ({
		...share(
			group.reduce((a, r) => a + r.active![HEADLINE_WEEK], 0),
			group.reduce((a, r) => a + r.size, 0)
		),
		from: group[0].week,
		to: group[group.length - 1].week
	});
	// Oldest first, so the newer half is the tail (the larger one when odd).
	return { earlier: part(reached.slice(0, half)), recent: part(reached.slice(half)) };
}
