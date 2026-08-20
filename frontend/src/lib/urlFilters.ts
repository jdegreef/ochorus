/**
 * Filters that live in the URL.
 *
 * A filtered shelf is a place, not a mode: "Spurgeon, translated only" should
 * survive a reload, come back with the Back button, and be something you can
 * send to someone. Biographies and Search worked that way; the Books shelf did
 * not — its filters were component state, so a shared /books link always landed
 * on the unfiltered shelf and Back stepped off the page instead of undoing the
 * last filter.
 *
 * The three functions here are the whole contract, and they are pure so the
 * rules — omit defaults, refuse values that are not on the list — can be tested
 * once instead of re-argued per page. `searchState.ts` is the search page's own
 * typed view built on top of them, adding only the coupling those two rules
 * cannot express (a facet means nothing without a query; `?in=` is a
 * `kind:slug` pair). The wiring — loop guard, debounce, prerender safety —
 * lives in `urlFilters.svelte.ts` beside this file.
 *
 * Note what does NOT belong here: view preferences (grid vs list, sort order).
 * Those describe the reader, not the shelf, and belong in localStorage — a
 * shared link should carry what is being shown, not how someone likes to look
 * at it.
 */

export type Filters = Record<string, string>;

/**
 * A stable string for a set of filter values, used as the loop guard between
 * the writer (state → URL) and the reader (URL → state): when a page's own
 * write comes back through the reader, the key matches and it falls through.
 */
export function filterKey(values: Filters): string {
	return Object.keys(values)
		.sort()
		.map((k) => `${k}=${values[k].trim()}`)
		.join('|');
}

/**
 * Write `values` onto a copy of `url`, dropping any that equal their default so
 * a pristine view stays a clean `/books` rather than `/books?q=&source=all`.
 */
export function writeFilters(url: URL, values: Filters, defaults: Filters): URL {
	const next = new URL(url);
	for (const [k, v] of Object.entries(values)) {
		const trimmed = v.trim();
		if (!trimmed || trimmed === defaults[k]) next.searchParams.delete(k);
		else next.searchParams.set(k, trimmed);
	}
	return next;
}

/**
 * Read filters back out of a query string.
 *
 * `allowed` is per-key: a key listed there is an enum and anything off the list
 * falls back to the default (a hand-edited `?source=nonsense` must not put the
 * shelf into a state its own controls can't show). A key absent from `allowed`
 * is free text — a search term, a topic slug — and is taken as given.
 */
export function readFilters<T extends Filters>(
	params: URLSearchParams,
	defaults: T,
	allowed: Partial<Record<keyof T, readonly string[]>> = {}
): T {
	const out = { ...defaults };
	for (const key of Object.keys(defaults) as (keyof T)[]) {
		const raw = params.get(String(key));
		if (raw === null) continue;
		const list = allowed[key];
		if (list && !list.includes(raw)) continue;
		out[key] = raw as T[keyof T];
	}
	return out;
}
