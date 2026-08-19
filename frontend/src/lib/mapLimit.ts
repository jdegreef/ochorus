/**
 * Map over items concurrently, with a ceiling on how many run at once.
 *
 * `Promise.all(items.map(fn))` is the usual reflex, and for a handful of items
 * it is the right one. It stops being right when the list is as long as a
 * reader's history: the notebook rebuilds every highlighted chapter, sermon and
 * biography, so an unbounded fan-out would open one request per highlight and
 * hand the API a burst proportional to how much someone has read. A serial loop
 * has the opposite problem — it is one round-trip deep per item, and the page
 * sits blank through all of them.
 *
 * Results come back in input order regardless of which finished first, and a
 * rejection propagates like `Promise.all`'s — callers that want per-item
 * tolerance catch inside `fn`, which is what the notebook does so one offline
 * chapter doesn't blank the page.
 */
export async function mapLimit<T, R>(
	items: readonly T[],
	limit: number,
	fn: (item: T, index: number) => Promise<R>
): Promise<R[]> {
	const out = new Array<R>(items.length);
	let next = 0;
	const workers = Array.from({ length: Math.max(1, Math.min(limit, items.length)) }, async () => {
		// Each worker takes the next index until the list runs out, so a slow
		// item holds up only itself — not a fixed slice of the work.
		while (next < items.length) {
			const i = next++;
			out[i] = await fn(items[i], i);
		}
	});
	await Promise.all(workers);
	return out;
}

/**
 * How many library requests the notebook keeps in flight. Browsers cap
 * same-origin connections around six, so going higher buys queueing rather than
 * speed — and this is a bound on what one page asks of the API, not a target.
 */
export const NOTEBOOK_CONCURRENCY = 6;
