/**
 * What the browser may tell Sentry, and what it may not.
 *
 * Sentry records the page URL on every event and the URL of every navigation
 * and fetch in its breadcrumbs. On this site those carry secrets and reader
 * text: Supabase returns from sign-in with the session in the URL hash
 * (`#access_token=…&refresh_token=…`) or a `?code=` / `?token_hash=` to
 * exchange, and search sends what the reader typed as `?q=`. The backend keeps
 * the same line (`send_default_pii=False`, and search logs at warning level so
 * `?q=` never reaches an event). This is the browser's half.
 *
 * The hash is dropped outright, since nothing in it is worth a debugging trail.
 * Query values are kept, because `?language=` and `?page=` are exactly the
 * context a bug report needs, except for the keys below, whose values are
 * replaced.
 */
const SECRET_PARAMS = new Set([
	'q',
	'query',
	'code',
	'token',
	'token_hash',
	'access_token',
	'refresh_token',
	'email',
	'error_description'
]);

export const REDACTED = '[redacted]';

/** `url` without its hash and with secret query values replaced. A value that
 * isn't a URL at all comes back unchanged; there's nothing to scrub. */
export function scrubUrl(url: string): string {
	let parsed: URL;
	try {
		// A base, so relative fetch URLs (`/api/library/search/?q=…`) parse too.
		parsed = new URL(url, 'https://x.invalid');
	} catch {
		return url;
	}
	parsed.hash = '';
	for (const key of [...parsed.searchParams.keys()]) {
		if (SECRET_PARAMS.has(key.toLowerCase())) parsed.searchParams.set(key, REDACTED);
	}
	const out = parsed.toString();
	// Hand a relative URL back relative, as it came.
	return parsed.origin === 'https://x.invalid' && !url.startsWith('https://x.invalid')
		? out.slice('https://x.invalid'.length)
		: out;
}

/** Absolute URLs and API paths inside free text, such as a console line. */
const URL_IN_TEXT = /https?:\/\/[^\s"'`<>]+|\/api\/[^\s"'`<>]+/g;

/** `text` with every URL in it scrubbed. The API's retry warning logs the
 * request URL (`[api] … from …/search/?q=… — retrying`), and Sentry keeps
 * console lines as breadcrumbs, so URLs in prose need the same treatment. */
export const scrubText = (text: string) => text.replace(URL_IN_TEXT, scrubUrl);

/** The fields of an event and a breadcrumb this module rewrites, typed
 * structurally so the module needs no Sentry import (the SDK loads lazily). */
interface ScrubbableEvent {
	request?: { url?: string; query_string?: unknown };
	exception?: { values?: { value?: string }[] };
	breadcrumbs?: ScrubbableBreadcrumb[];
}
interface ScrubbableBreadcrumb {
	message?: string;
	data?: Record<string, unknown>;
}

const URL_FIELDS = ['url', 'from', 'to'] as const;

export function scrubBreadcrumb<B extends ScrubbableBreadcrumb>(crumb: B): B {
	if (crumb.message) crumb.message = scrubText(crumb.message);
	if (!crumb.data) return crumb;
	for (const field of URL_FIELDS) {
		const value = crumb.data[field];
		if (typeof value === 'string') crumb.data[field] = scrubUrl(value);
	}
	// A console breadcrumb keeps the logged values as `data.arguments`.
	const args = crumb.data.arguments;
	if (Array.isArray(args)) {
		crumb.data.arguments = args.map((a) => (typeof a === 'string' ? scrubText(a) : a));
	}
	return crumb;
}

export function scrubEvent<E extends ScrubbableEvent>(event: E): E {
	if (event.request?.url) event.request.url = scrubUrl(event.request.url);
	// The SDK also copies the query out on its own; the scrubbed URL carries it.
	if (event.request) delete event.request.query_string;
	// An error's message can quote a URL as well.
	for (const ex of event.exception?.values ?? []) {
		if (ex.value) ex.value = scrubText(ex.value);
	}
	event.breadcrumbs?.forEach(scrubBreadcrumb);
	return event;
}

/**
 * An error a reader's browser throws that says nothing about this site:
 * extensions, a ResizeObserver that simply ran late, a fetch that failed
 * because the reader went offline. Sentry's free plan has a monthly quota, and
 * these would spend it on noise.
 */
export const IGNORE_ERRORS: (string | RegExp)[] = [
	'ResizeObserver loop limit exceeded',
	'ResizeObserver loop completed with undelivered notifications',
	/^Non-Error promise rejection captured/
	// A failed fetch ("Failed to fetch", "Load failed", "NetworkError…") is NOT
	// ignored: offline readers are dropped by isOffline, and an online reader
	// who can't reach the API is the outage this exists to show.
];

/** Only errors thrown from our own bundle; an extension's or an injected
 * script's stack frames point elsewhere. */
export const ALLOW_URLS: RegExp[] = [/\/_app\/immutable\//];

/** Whether to drop an event because the reader is offline: an offline reader's
 * failed fetches are their connection, not our bug. */
export const isOffline = () => typeof navigator !== 'undefined' && navigator.onLine === false;
