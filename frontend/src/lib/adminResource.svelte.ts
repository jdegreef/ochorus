/**
 * The load lifecycle every admin page repeats.
 *
 * Nine admin pages opened with the same twenty-five lines: four state fields,
 * a monotonic request id, a try/catch that sorts 401/403 from everything else,
 * and an `$effect` that waits for auth to settle. Nine copies of a block whose
 * two subtle parts are the ones you would never notice were missing.
 *
 * The subtleties are why this is shared rather than merely tidy:
 *
 *  - **The sequence guard.** Auth settles asynchronously, so a page mounts,
 *    fires an anonymous request, and then fires an authenticated one when the
 *    Supabase session restores. Without `seq`, whichever lands last wins — and
 *    the anonymous 401 frequently lands last, so an admin sees "Not authorised"
 *    on a page they have every right to.
 *  - **Waiting for `auth.initialized`.** Fire before the session is restored
 *    and that first request 401s by construction, flashing the same false
 *    denial. `auth.enabled` is checked first because a build without Supabase
 *    configured never initializes at all and would otherwise hang on "Loading…".
 *
 * A tenth page written by copying a ninth inherits both by luck. A tenth page
 * written on this helper inherits them by construction — which is exactly what
 * `/admin/import` did not do: it has no gate at all, and an unauthorised import
 * surfaces as a raw API error string in the upload form.
 */
import { untrack } from 'svelte';
import { ApiError } from '$lib/api';
import { auth } from '$lib/auth.svelte';

/** The load state of one admin endpoint. */
export class AdminResource<T> {
	/** The loaded payload, or null until the first successful load. */
	data = $state<T | null>(null);
	/** True while a request is in flight — including refreshes over stale data. */
	loading = $state(true);
	/** The request came back 401/403: not signed in, or not an admin. */
	denied = $state(false);
	/** Anything else went wrong; the message is for display. */
	error = $state<string | null>(null);

	/** Monotonic request id — only the newest load's outcome is applied. */
	#seq = 0;
	readonly #fetcher: () => Promise<T>;
	readonly #message: string;
	readonly #onLoad?: (result: T) => void;

	constructor(fetcher: () => Promise<T>, message: string, onLoad?: (result: T) => void) {
		this.#fetcher = fetcher;
		this.#message = message;
		this.#onLoad = onLoad;
	}

	/**
	 * Re-run the fetch. Bound, so it can be handed straight to `onclick` for the
	 * Refresh and "Try again" buttons the pages render.
	 */
	load = async (): Promise<void> => {
		const id = ++this.#seq;
		this.loading = true;
		this.denied = false;
		this.error = null;
		try {
			const result = await this.#fetcher();
			if (id !== this.#seq) return; // superseded by a newer load
			this.data = result;
			// After the supersession check, so a stale load can't kick off the
			// follow-up requests a detail page chains off its payload.
			this.#onLoad?.(result);
		} catch (e) {
			if (id !== this.#seq) return;
			if (e instanceof ApiError && (e.status === 401 || e.status === 403)) this.denied = true;
			else this.error = e instanceof Error ? e.message : this.#message;
		} finally {
			if (id === this.#seq) this.loading = false;
		}
	};
}

/**
 * An {@link AdminResource} that loads itself once auth has settled, and again
 * whenever the signed-in identity changes.
 *
 * Call this at the top level of a page's `<script>`: it registers an `$effect`,
 * so it needs component-initialisation context.
 *
 * @param fetcher  Runs the request. For a detail page, close over the route
 *                 param (`() => getAdminBook(data.slug)`) and pass `key`.
 * @param message  Fallback text when the failure carries no message of its own.
 * @param key      Reactive values the load depends on beyond identity — read by
 *                 the effect itself, so a client-side navigation from
 *                 `/admin/books/a` to `/admin/books/b` re-fetches.
 * @param onLoad   Runs on a payload that wasn't superseded — for the follow-up
 *                 requests a detail page chains off what it just loaded.
 *
 * The fetch runs `untrack`ed, so the parameters above are the whole dependency
 * set. Without that they would not be: an async function's reads before its
 * first `await` are tracked like any others, so a fetcher that builds a query
 * out of six filter fields quietly makes all six dependencies. The review queue
 * did exactly that, and every filter change ran a redundant second `load()` on
 * top of the one the filter's own handler had already called. It cost a wasted
 * call rather than a wasted round-trip only because `apiFetch` happens to
 * collapse concurrent identical GETs — a dependency set that is accidental, and
 * an overlap that is coincidental, are two things to be relying on at once.
 */
export function adminResource<T>(
	fetcher: () => Promise<T>,
	message: string,
	key?: () => unknown,
	onLoad?: (result: T) => void
): AdminResource<T> {
	const resource = new AdminResource(fetcher, message, onLoad);
	$effect(() => {
		key?.();
		if (auth.enabled && !auth.initialized) return;
		void auth.user?.email;
		untrack(() => void resource.load());
	});
	return resource;
}
