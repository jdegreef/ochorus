import { goto } from '$app/navigation';
import { filterKey, readFilters, writeFilters, type Filters } from './urlFilters';

/**
 * A shelf's filters, kept in the URL, wired up once.
 *
 * `urlFilters.ts` beside this file owns the ENCODING (omit defaults, refuse
 * values off the list). This owns the WIRING, which is the fiddly half: the
 * loop guard that tells "the reader navigated" from "we wrote the URL", the
 * rule that state must not be read from the query string during setup, the
 * `goto` options that keep a filtered view out of the history and off the
 * scroll restorer, and the debounce that stops a keystroke being a navigation.
 *
 * All of that was hand-written per page, so every control had to remember to
 * call `syncUrl()` after assigning — `onclick={() => ((source = x), syncUrl())}`
 * — and a control that forgot silently dropped its filter from the URL. Here
 * the sync is an effect over the values themselves, so there is nothing to
 * forget: set `filters.values.source` and the URL follows.
 *
 * Deliberately NOT for view preferences (grid vs list, sort order). Those
 * describe the reader, not the shelf, and belong in localStorage — a shared
 * link should carry what is being shown, not how someone likes to look at it.
 */
export function urlFilters<T extends Filters>(config: {
	/** Every filter this shelf has, at its default. Shape and keys come from here. */
	defaults: T;
	/**
	 * Per-key value lists. A key listed here is an enum and anything else in the
	 * URL falls back to the default; a key absent is free text (a search term, a
	 * topic slug) and is taken as given.
	 */
	allowed?: Partial<Record<keyof T, readonly string[]>>;
	/**
	 * The current URL, read reactively — `() => $page.url`.
	 *
	 * A callback rather than the URL itself because this has to re-read it when
	 * the reader navigates (a shared link, Back, Forward). It must NOT be read
	 * during setup: SvelteKit forbids query-param access while prerendering, and
	 * a prerendered page's HTML must not depend on a query string anyway, since
	 * it is what gets served for the bare `/books`.
	 */
	url: () => URL;
	/**
	 * How long to wait before writing. A filter you type wants a pause (search
	 * debounces by 250ms for the same reason); a filter you click wants none,
	 * and gets none — the debounce restarts per change, so a click that follows
	 * a pause writes immediately.
	 */
	debounceMs?: number;
}) {
	const { defaults, allowed = {}, url, debounceMs = 250 } = config;

	const values = $state({ ...defaults } as T);
	/** Shared by the writer and the reader below; not reactive, on purpose. */
	let urlState = filterKey(defaults);
	let timer: ReturnType<typeof setTimeout> | undefined;

	const snapshot = (): T => ({ ...values });

	// URL → state, for shared links and Back/Forward. Runs first on mount, which
	// is what hydrates the page from a shared link.
	$effect(() => {
		const next = readFilters(url().searchParams, defaults, allowed);
		const key = filterKey(next);
		if (key === urlState) return;
		urlState = key;
		clearTimeout(timer);
		Object.assign(values, next);
	});

	// state → URL. Reading every value through filterKey is what subscribes this
	// effect to all of them, so a new control needs no wiring at all.
	$effect(() => {
		const next = snapshot();
		const key = filterKey(next);
		if (key === urlState) return;
		clearTimeout(timer);
		timer = setTimeout(() => {
			urlState = key;
			goto(writeFilters(url(), next, defaults), {
				replaceState: true,
				keepFocus: true,
				noScroll: true
			});
		}, debounceMs);
		return () => clearTimeout(timer);
	});

	return {
		/** The live filter values. Bind straight to them. */
		values,
		/** Back to defaults — the "clear filters" affordance. */
		reset(keep: Partial<T> = {}) {
			Object.assign(values, defaults, keep);
		},
		/** True when anything is narrowing the shelf. */
		get active(): boolean {
			return filterKey(snapshot()) !== filterKey(defaults);
		}
	};
}
