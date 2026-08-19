/**
 * A ceiling on how many async calls run at once.
 *
 * `Promise.all(items.map(fn))` is the usual reflex, and for a handful of items
 * it is the right one. It stops being right when the list is as long as a
 * reader's history: the notebook rebuilds every highlighted chapter, sermon and
 * biography, so an unbounded fan-out would open one request per highlight and
 * hand the API a burst proportional to how much someone has read. A serial loop
 * has the opposite problem — one round-trip deep per item, with the page blank
 * throughout.
 *
 * The ceiling belongs to a limiter shared by everything talking to the same
 * API, not to a call site. A per-call limit composes by multiplying: three
 * lanes of six, each fanning out six more, is forty-eight requests in flight
 * while every individual call looks correctly bounded.
 *
 * **Gate the leaf call, never the work that awaits one.** A task holding a slot
 * while it waits for a slot is a deadlock, and with every slot held by such a
 * task it is a permanent one. So wrap the `fetch`, and let `Promise.all` do the
 * structure around it:
 *
 * ```ts
 * const gate = createLimiter(6);
 * await Promise.all(books.map(async (slug) => {
 *   const book = await gate(() => getBook(slug));           // ✓ leaf
 *   const chapters = await Promise.all(
 *     book.chapters.map((c) => gate(() => getChapter(slug, c.order)))
 *   );
 * }));
 * ```
 */

/** Admits work under a shared ceiling. Await it; it resolves with `fn`'s value. */
export type Limiter = <R>(fn: () => Promise<R>) => Promise<R>;

/** A limiter admitting at most `limit` concurrent calls. */
export function createLimiter(limit: number): Limiter {
	const ceiling = Math.max(1, limit);
	let active = 0;
	const waiting: (() => void)[] = [];

	// A finished call hands its slot DIRECTLY to the next waiter rather than
	// decrementing and letting it re-take one. The waiter resumes on a later
	// microtask, and in that gap a fresh caller would see a free slot and take
	// it too — briefly exceeding the ceiling the caller was promised.
	const release = () => {
		const next = waiting.shift();
		if (next) next();
		else active--;
	};

	return async function run<R>(fn: () => Promise<R>): Promise<R> {
		if (active >= ceiling) await new Promise<void>((resolve) => waiting.push(resolve));
		else active++;
		try {
			return await fn();
		} finally {
			release();
		}
	};
}

/**
 * How many library requests the notebook keeps in flight, across all of its
 * sections at once. Browsers cap same-origin connections around six, so going
 * higher buys queueing rather than speed — and this is a bound on what one page
 * asks of the API, not a target.
 */
export const NOTEBOOK_CONCURRENCY = 6;
