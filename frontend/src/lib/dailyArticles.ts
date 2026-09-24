// "Eight for today" — the home page's daily article pick.
//
// Deterministic, so every visitor sees the same eight on the same day and the
// set turns over at local midnight with no manual step (the daily sibling of
// SermonOfTheWeek's weekly pick). Picked CLIENT-SIDE by the caller: the home
// page is prerendered, and choosing at build time would freeze the set on
// whatever day the site last deployed.
//
// The shelf is first put in a fixed shuffled order (by a hash of each slug), so
// a day's eight mix the book guides and the question articles instead of eight
// neighbours from the API's sort order. Days then walk that order in windows of
// `count`, wrapping, so every article comes round in turn — and adding or
// removing one article shifts the order only slightly rather than reshuffling
// every future day.

/** FNV-1a — a small, stable string hash; quality only needs to scatter slugs. */
function hash(s: string): number {
	let h = 0x811c9dc5;
	for (let i = 0; i < s.length; i++) {
		h ^= s.charCodeAt(i);
		h = Math.imul(h, 0x01000193);
	}
	return h >>> 0;
}

/** Whole days since the epoch for the reader's LOCAL calendar date. */
export function localDayNumber(d: Date): number {
	return Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86_400_000);
}

export function pickDailyArticles<T extends { slug: string }>(
	articles: readonly T[],
	date: Date,
	count = 8
): T[] {
	if (articles.length <= count) return [...articles];
	const order = [...articles].sort((a, b) => hash(a.slug) - hash(b.slug) || a.slug.localeCompare(b.slug));
	const n = order.length;
	const start = (((localDayNumber(date) * count) % n) + n) % n;
	return Array.from({ length: count }, (_, i) => order[(start + i) % n]);
}
