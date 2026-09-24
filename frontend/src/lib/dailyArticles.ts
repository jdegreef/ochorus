// "Eight for today" — the home page's daily article pick.
//
// Deterministic, so every visitor sees the same eight on the same day and the
// set turns over at local midnight with no manual step (the daily sibling of
// SermonOfTheWeek's weekly pick). Picked CLIENT-SIDE by the caller: the home
// page is prerendered, and choosing at build time would freeze the set on
// whatever day the site last deployed.
//
// Each article gets a score from a hash of (slug, day) and the day's picks are
// the `count` lowest. Scoring each article on its own, rather than walking a
// window over the list, is what keeps a content deploy from reshuffling the
// day: publishing or unpublishing one article changes today's set by at most
// that one article, where a `day % shelf-size` window would jump to an
// unrelated eight mid-afternoon. Across days the picks are a fresh random draw,
// so every article comes up regularly without a fixed rota.

/**
 * FNV-1a plus MurmurHash3's 32-bit finalizer. The finalizer is load-bearing:
 * bare FNV-1a scatters near-identical keys (`slug:20354`, `slug:20355`) so
 * poorly that the same few articles won day after day — measured, a month of
 * picks reached 34 of 130 articles; with the finalizer, ~113 (a fair draw).
 */
function hash(s: string): number {
	let h = 0x811c9dc5;
	for (let i = 0; i < s.length; i++) {
		h ^= s.charCodeAt(i);
		h = Math.imul(h, 0x01000193);
	}
	h ^= h >>> 16;
	h = Math.imul(h, 0x85ebca6b);
	h ^= h >>> 13;
	h = Math.imul(h, 0xc2b2ae35);
	h ^= h >>> 16;
	return h >>> 0;
}

/** Whole days since the epoch for the reader's LOCAL calendar date. */
export function localDayNumber(d: Date): number {
	return Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86_400_000);
}

/**
 * The day's `count` articles, or [] when the shelf has fewer than `count` —
 * the section's heading promises that many, so a short shelf shows nothing.
 */
export function pickDailyArticles<T extends { slug: string }>(
	articles: readonly T[],
	date: Date,
	count = 8
): T[] {
	if (articles.length < count) return [];
	const day = localDayNumber(date);
	return articles
		.map((a) => ({ a, score: hash(`${a.slug}:${day}`) }))
		.sort((x, y) => x.score - y.score || x.a.slug.localeCompare(y.a.slug))
		.slice(0, count)
		.map((x) => x.a);
}
