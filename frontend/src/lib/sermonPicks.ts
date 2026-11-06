/**
 * The sermons shelf's curated order (design review #28, "Sermons: three to
 * start with"). A newcomer doesn't know M'Cheyne from Maclaren, and the API's
 * own order is preacher-by-preacher in alphabetical order — so a flat list of
 * it opened on fifteen A. B. Simpsons. Two pure helpers, built from the shelf
 * the page already loads (no request of their own), tested beside them
 * (`sermonPicks.test.ts`):
 *
 * - **`startWith`**: the "Start with these" row — the one hand list,
 *   `START_WITH`, in its own order. A language that lacks some of them (most
 *   translated shelves are young) tops the row up from `featuredOrder`, one
 *   sermon per preacher it doesn't already show, so the row never shows a
 *   dead card and never invents a pick.
 * - **`featuredOrder`**: the "Featured" sort of the flat list — the preachers
 *   taking turns, each walking their own sequence (the API's per-preacher
 *   `sort_order`), so the first screen is a sampler of the shelf rather than
 *   one alphabetically lucky preacher. The deepest shelves go first; ties by
 *   name, so the order is stable.
 */

interface PickSermon {
	slug: string;
	author: { slug: string; name: string };
}

/** Three sermons to start with, by slug — the only hand list. Short, plainly
 *  told and from three different pulpits: Spurgeon on prayer, Tozer on God,
 *  M'Cheyne's fourteen minutes on a minister's own soul. */
export const START_WITH = ['the-golden-key-of-prayer', 'the-infinite-god', 'a-castaway'] as const;

/** How many the row shows. */
export const START_COUNT = 3;

/** The shelf in featured order: one sermon from each preacher in turn, the
 *  deepest shelves first. `defer` names sermons to move to the end of their
 *  preacher's turn — the ones the "Start with these" row already shows, so
 *  the list under it doesn't open by repeating it. */
export function featuredOrder<T extends PickSermon>(
	sermons: readonly T[],
	defer: ReadonlySet<string> = new Set()
): T[] {
	const byPreacher = new Map<string, T[]>();
	for (const s of sermons) {
		const own = byPreacher.get(s.author.slug);
		if (own) own.push(s);
		else byPreacher.set(s.author.slug, [s]);
	}
	const queues = [...byPreacher.values()]
		.map((q) => [...q.filter((s) => !defer.has(s.slug)), ...q.filter((s) => defer.has(s.slug))])
		.sort((a, b) => b.length - a.length || a[0].author.name.localeCompare(b[0].author.name));
	const out: T[] = [];
	for (let i = 0; out.length < sermons.length; i++)
		for (const q of queues) if (i < q.length) out.push(q[i]);
	return out;
}

/** The "Start with these" row: the hand picks present in this language, topped
 *  up from featured order with preachers the row doesn't show yet. Empty when
 *  the shelf can't fill the row, so the caller hides it rather than showing a
 *  row of one. */
export function startWith<T extends PickSermon>(sermons: readonly T[]): T[] {
	const bySlug = new Map(sermons.map((s) => [s.slug, s]));
	const picks = START_WITH.map((s) => bySlug.get(s)).filter((s): s is T => !!s);
	if (picks.length >= START_COUNT) return picks.slice(0, START_COUNT);
	const preachers = new Set(picks.map((s) => s.author.slug));
	for (const s of featuredOrder(sermons)) {
		if (picks.length >= START_COUNT) break;
		if (preachers.has(s.author.slug)) continue;
		picks.push(s);
		preachers.add(s.author.slug);
	}
	return picks.length >= START_COUNT ? picks.slice(0, START_COUNT) : [];
}
