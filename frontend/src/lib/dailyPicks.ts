/**
 * Deterministic daily rotation of shelf items.
 *
 * A calendar day is the seed, so every visitor sees the same picks all day and
 * they advance automatically at midnight (local time — the not-found page
 * renders client-side, so `dayNumber()` reads the viewer's own date). Picks
 * favour VARIETY: `pickByDay` returns items with distinct author keys, and you
 * can pass already-chosen keys to `exclude` so a second call (e.g. sermons)
 * avoids the people a first call (books) already featured.
 */

/** Whole days since the Unix epoch, in the viewer's local timezone. */
export function dayNumber(now: Date = new Date()): number {
	return Math.floor(
		(now.getTime() - now.getTimezoneOffset() * 60_000) / 86_400_000
	);
}

/** Small, fast, well-distributed seeded PRNG (mulberry32). */
function mulberry32(seed: number): () => number {
	let a = seed >>> 0;
	return () => {
		a = (a + 0x6d2b79f5) | 0;
		let t = Math.imul(a ^ (a >>> 15), 1 | a);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4_294_967_296;
	};
}

function shuffle<T>(items: readonly T[], rnd: () => number): T[] {
	const a = [...items];
	for (let i = a.length - 1; i > 0; i--) {
		const j = Math.floor(rnd() * (i + 1));
		[a[i], a[j]] = [a[j], a[i]];
	}
	return a;
}

/**
 * Pick `count` items for `seed`, maximising the number of distinct `key`s
 * (people). In order of preference:
 *   1. distinct keys NOT in `exclude` — so a second shelf avoids the people a
 *      first one already featured, when it can afford to;
 *   2. distinct keys including excluded ones — variety within this shelf beats a
 *      cross-shelf clash on a small catalogue;
 *   3. balanced backfill — when there aren't `count` distinct keys, add the
 *      least-used key first so picks don't cluster on one person (2/1/1, not 3/1).
 * Pure and deterministic: same (items, count, seed, exclude) → same result.
 */
export function pickByDay<T>(
	items: readonly T[],
	count: number,
	seed: number,
	key: (item: T) => string,
	exclude: Iterable<string> = []
): T[] {
	const order = shuffle(items, mulberry32(seed));
	const excluded = new Set(exclude);
	const usedKeys = new Set<string>();
	const picks: T[] = [];

	const takeDistinct = (skipExcluded: boolean) => {
		for (const item of order) {
			if (picks.length === count) break;
			const k = key(item);
			if (usedKeys.has(k) || (skipExcluded && excluded.has(k))) continue;
			usedKeys.add(k);
			picks.push(item);
		}
	};
	takeDistinct(true);
	takeDistinct(false);

	// Balanced backfill: repeatedly add the leftover item whose key is used least.
	const remaining = order.filter((it) => !picks.includes(it));
	while (picks.length < count && remaining.length) {
		const counts = new Map<string, number>();
		for (const p of picks) counts.set(key(p), (counts.get(key(p)) ?? 0) + 1);
		let best = 0;
		for (let i = 1; i < remaining.length; i++) {
			if ((counts.get(key(remaining[i])) ?? 0) < (counts.get(key(remaining[best])) ?? 0)) best = i;
		}
		picks.push(remaining.splice(best, 1)[0]);
	}
	return picks;
}
