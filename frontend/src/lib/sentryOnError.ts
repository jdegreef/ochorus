/**
 * Load the Sentry SDK on the first error, not on every visit.
 *
 * The SDK is the largest file in the build (~437 KB raw, ~145 KB gzipped).
 * Loading it on idle kept it off the first tap, but every new visitor still
 * downloaded and parsed it, on a phone on a slow connection too, for code that
 * runs on almost no visits. This module stands in until an error happens: two
 * small listeners hold the first few errors, and the first one that comes from
 * our own bundle loads the SDK and hands them over. From then on Sentry's own
 * global handlers (installed by `init`) take over, so these listeners remove
 * themselves.
 *
 * What we give up: breadcrumbs (clicks, navigations, console lines) from before
 * the SDK loaded. The error itself, its stack and its page still arrive.
 * SvelteKit's own `handleError` (hooks.client.ts) still loads the SDK on
 * demand for load and render errors.
 */

/** The SDK surface this needs: just enough to hand over buffered errors. */
export interface CaptureSdk {
	captureException(error: unknown): unknown;
}

export interface ArmOptions {
	/** Loads (and initialises) the SDK. Called at most once. */
	load: () => Promise<CaptureSdk>;
	/** Stack-frame URL patterns that mark an error as ours (sentryScrub
	 *  ALLOW_URLS). An error whose script URL matches none of them, such as an
	 *  extension's or an injected script's, does not load the SDK, since Sentry
	 *  would drop it anyway. Omitted in dev, where modules come from /src/. */
	allowUrls?: RegExp[];
	/** The window to listen on (a test passes its own). */
	target?: Pick<Window, 'addEventListener' | 'removeEventListener'>;
}

/** How many errors to hold while the SDK downloads. One page that throws in a
 *  loop must not grow this without bound. */
export const BUFFER_LIMIT = 10;

/** Whether a window `error` event came from a script we can attribute to our
 *  bundle. A missing filename (a cross-origin "Script error." has none, and
 *  some browsers leave it empty for inline handlers) is treated as ours: it is
 *  rare, and losing a real error costs more than one extra download. */
export function isOwnError(event: Pick<ErrorEvent, 'filename'>, allowUrls?: RegExp[]): boolean {
	if (!allowUrls || !event.filename) return true;
	return allowUrls.some((re) => re.test(event.filename));
}

/**
 * Listen for the first error and load the SDK then. Returns a function that
 * removes the listeners (tests; nothing in the app needs to call it).
 */
export function armSentryOnError({ load, allowUrls, target = window }: ArmOptions): () => void {
	const held: unknown[] = [];
	let loading = false;

	const hold = (error: unknown) => {
		if (held.length < BUFFER_LIMIT) held.push(error);
		if (loading) return;
		loading = true;
		// From here Sentry's own handlers will see new errors; stop listening
		// once it has loaded, so nothing is reported twice.
		load()
			.then((sdk) => {
				disarm();
				for (const error of held.splice(0)) sdk.captureException(error);
			})
			.catch(() => {
				// The SDK failed to load (offline, blocked). Nothing to report to;
				// stop holding errors so the buffer is released.
				disarm();
				held.length = 0;
			});
	};

	const onError = (event: Event) => {
		const e = event as ErrorEvent;
		if (!isOwnError(e, allowUrls)) return;
		hold(e.error ?? new Error(e.message || 'Unknown error'));
	};
	const onRejection = (event: Event) => {
		hold((event as PromiseRejectionEvent).reason);
	};

	function disarm() {
		target.removeEventListener('error', onError);
		target.removeEventListener('unhandledrejection', onRejection);
	}

	target.addEventListener('error', onError);
	target.addEventListener('unhandledrejection', onRejection);
	return disarm;
}
