/**
 * Pure helpers for the leader's guide page (/books/<slug>/guide).
 */

/**
 * A week's heading: the localized "Week %n%" and the chapter's own title,
 * joined by an em dash — "Week 3 — The Slough of Despond". A chapter with no
 * title keeps the week alone rather than ending on a dangling dash.
 */
export function guideWeekHeading(template: string, week: number, title: string): string {
	const label = template.replace('%n%', String(week));
	const name = title.trim();
	return name ? `${label} — ${name}` : label;
}
