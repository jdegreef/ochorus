// "Sermon of the day" — the home page's (and sermons shelf's) daily pick.
//
// Deterministic, so every visitor sees the same sermon on the same day and it
// turns over at local midnight with no manual step. Picked CLIENT-SIDE by the
// caller, for the same reason as dailyArticles: the pages are prerendered.
//
// The rotation walks PREACHERS, not sermons, so tomorrow is always someone
// new: day N is preacher N mod P. A sermon-level draw would hand Spurgeon (by
// far the deepest shelf) most days and could repeat him back to back. The
// preachers' order is a fixed hash shuffle rather than alphabetical, so the
// week doesn't read A, B, C; each preacher's own sermons take turns on the
// days that preacher comes round, so the whole shelf is reached over time.

import { hash, localDayNumber } from '$lib/dailyArticles';

/** The day's sermon, or null on an empty shelf. */
export function pickDailySermon<T extends { slug: string; author: { slug: string } }>(
	sermons: readonly T[],
	date: Date
): T | null {
	if (!sermons.length) return null;
	const byPreacher = new Map<string, T[]>();
	for (const s of sermons) {
		const own = byPreacher.get(s.author.slug);
		if (own) own.push(s);
		else byPreacher.set(s.author.slug, [s]);
	}
	const shuffled = (slugs: string[]) =>
		slugs.sort((a, b) => hash(a) - hash(b) || a.localeCompare(b));
	const preachers = shuffled([...byPreacher.keys()]);
	const day = localDayNumber(date);
	const own = byPreacher.get(preachers[day % preachers.length])!;
	const order = shuffled(own.map((s) => s.slug));
	const slug = order[Math.floor(day / preachers.length) % order.length];
	return own.find((s) => s.slug === slug)!;
}
