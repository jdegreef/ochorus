import { building } from '$app/environment';
import { API_BASE_URL } from './config';

export class ApiError extends Error {
	status: number;
	body: unknown;
	constructor(status: number, body: unknown) {
		super(`API ${status}`);
		this.status = status;
		this.body = body;
	}
}

/**
 * The body of a failed response: parsed JSON when it is JSON (DRF errors are,
 * so callers can read `.detail`), otherwise the raw text.
 *
 * ONE read. This was `res.json()` with a `res.text()` fallback in its catch —
 * but a failed `res.json()` has already consumed the stream, so the fallback
 * always rejected and was swallowed into `null`. Every non-JSON error body
 * therefore arrived as `body: null`: exactly the HTML 502/503 pages Render's
 * proxy serves during an outage, which is when the body is the only clue there
 * is. The fallback the code appeared to offer was dead from the start.
 */
async function errorBody(res: Response): Promise<unknown> {
	const text = await res.text().catch(() => null);
	// An empty body stays `null` rather than becoming `''` — callers test the
	// body for truthiness, and that is what they got before this change.
	if (!text) return null;
	try {
		return JSON.parse(text);
	} catch {
		return text;
	}
}

/**
 * The `fetch` a SvelteKit load() receives. Pass it through (the optional last
 * argument of `apiFetch` and the public loaders) from every page load.
 *
 * Why: public pages are prerendered, then HYDRATE by running load() again in the
 * browser. With the global `fetch` that second run calls the API — a round-trip
 * before the page is live, egress for every visit, and a hard dependency on the
 * API answering. Googlebot's renderer is where that bit: when it could not reach
 * the API (robots.txt, 2026-09), the load threw, the page hydrated into
 * +error.svelte, and Google indexed its noindex. SvelteKit's own `fetch` instead
 * inlines each response into the prerendered HTML (`<script
 * data-sveltekit-fetched>`) and replays it on hydration, so the API is not asked
 * at all. A request that does not match what the prerender recorded (a signed-in
 * reader's Authorization header, a different language) just goes to the network
 * as before. Build-side CORS for these fetches: see `handleFetch` in
 * hooks.server.ts.
 */
export type Fetch = typeof fetch;

/**
 * Supplies the current Supabase access token, if any. The auth store registers
 * this (via `setAuthTokenProvider`) so we avoid an import cycle: api ↔ auth.
 */
let tokenProvider: () => string | null = () => null;

export function setAuthTokenProvider(fn: () => string | null) {
	tokenProvider = fn;
}

/**
 * During prerender, one flaky API response fails the whole deploy: the build
 * crawls every public page, a single 5xx bubbles up as a page error, and
 * SvelteKit (rightly) refuses to ship the half-broken page. The API restarting
 * mid-build has already cost a deploy this way (2026-08-13, a 500 on one
 * Spanish sermon page), so at build time idempotent requests retry transient
 * failures — network errors and 5xx — with a short backoff before giving up.
 * The last delay is long enough to ride out a Render API restart. Persistent
 * errors still fail the build: never ship a page that is genuinely broken.
 * At runtime nothing changes — retrying in the browser would only delay the
 * error UI.
 */
const BUILD_RETRY_DELAYS_MS = [1000, 4000, 10000];

const isIdempotent = (init: RequestInit) =>
	!init.method || ['GET', 'HEAD'].includes(init.method.toUpperCase());

async function robustFetch(url: string, init: RequestInit, f: Fetch = fetch): Promise<Response> {
	if (!building || !isIdempotent(init)) return f(url, init);
	for (let attempt = 0; ; attempt++) {
		const outOfRetries = attempt >= BUILD_RETRY_DELAYS_MS.length;
		let failure: string;
		try {
			const res = await f(url, init);
			if (res.status < 500 || outOfRetries) return res;
			failure = `${res.status}`;
		} catch (err) {
			if (outOfRetries) throw err;
			failure = String(err);
		}
		const delay = BUILD_RETRY_DELAYS_MS[attempt];
		console.warn(`[api] ${failure} from ${url} during prerender — retrying in ${delay}ms`);
		await new Promise((resolve) => setTimeout(resolve, delay));
	}
}

/**
 * Fetch wrapper for the Django API. The library is public (AllowAny), but when a
 * user is signed in we attach their Supabase Bearer token so authenticated
 * endpoints (e.g. /api/auth/me) work.
 */
async function requestJSON<T>(path: string, init: RequestInit, f?: Fetch): Promise<T> {
	const headers = new Headers(init.headers);
	if (init.body && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}
	const token = tokenProvider();
	if (token && !headers.has('Authorization')) {
		headers.set('Authorization', `Bearer ${token}`);
	}

	const res = await robustFetch(
		`${API_BASE_URL}${path}`,
		{ ...init, headers, signal: withTimeout(init.signal) },
		f
	);
	if (!res.ok) {
		throw new ApiError(res.status, await errorBody(res));
	}
	if (res.status === 204) return null as T;
	return (await res.json()) as T;
}

/**
 * How long a request may hang before it is abandoned.
 *
 * There was no timeout at all, so a request that never settles — a captive
 * portal, a dyno that accepted the connection and went away — left `loading`
 * true forever on every shelf and admin page. An error the reader can retry is
 * better than a spinner that never stops.
 *
 * Not applied during the build: prerender already has its own retry ladder
 * whose last delay is sized to ride out an API restart, and a 15s ceiling would
 * cut that short.
 */
const REQUEST_TIMEOUT_MS = 15_000;

/**
 * A signal that aborts after `ms`, preferring the native `AbortSignal.timeout`
 * and falling back to a manual controller where it is missing.
 *
 * `AbortSignal.timeout` and `AbortSignal.any` (below) are recent: iOS/macOS
 * Safari only gained them in 16.4 and 17.4 respectively. `withTimeout` runs on
 * EVERY request, so without this feature-detection an older-but-current mobile
 * Safari threw a `TypeError` out of the very first `apiFetch` — the whole reader
 * (shelves, search, chapter bodies all fetch through here) dead on arrival, with
 * no error UI to explain it. `AbortController` itself is universally supported
 * (Safari 11.1+), so the fallback leans on it.
 */
function timeoutSignal(ms: number): AbortSignal {
	if (typeof AbortSignal.timeout === 'function') return AbortSignal.timeout(ms);
	const controller = new AbortController();
	// A browser timer; aborting an already-settled fetch is a no-op, so the worst
	// case is one harmless fire `ms` after a request that finished sooner.
	setTimeout(() => controller.abort(), ms);
	return controller.signal;
}

/**
 * The union of several abort signals — aborts as soon as any of them does.
 * Prefers native `AbortSignal.any`, falling back to manual linking. See
 * {@link timeoutSignal} for why the fallback has to exist.
 */
function anySignal(signals: AbortSignal[]): AbortSignal {
	if (typeof AbortSignal.any === 'function') return AbortSignal.any(signals);
	const controller = new AbortController();
	for (const signal of signals) {
		if (signal.aborted) {
			controller.abort(signal.reason);
			break;
		}
		signal.addEventListener('abort', () => controller.abort(signal.reason), { once: true });
	}
	return controller.signal;
}

function withTimeout(caller: AbortSignal | null | undefined): AbortSignal | undefined {
	if (building) return caller ?? undefined;
	const timeout = timeoutSignal(REQUEST_TIMEOUT_MS);
	// Preserve a caller's own signal (the define popover aborts on new input).
	return caller ? anySignal([caller, timeout]) : timeout;
}

/**
 * In-flight GET requests, so concurrent callers asking for the same thing make
 * one request. Keyed by path AND token: two readers never share a response, and
 * a signed-in request never resolves from an anonymous one.
 *
 * The home page alone fired `listPlans` three times, `listBooks` twice and
 * `listSermons` twice on hydration — five components asking independently, all
 * at once, so neither the HTTP cache nor the service worker could dedupe them
 * (every lookup misses before the first response lands).
 *
 * NOTE: callers share ONE response object. That matches how this codebase
 * already treats API results — every sort copies first (`[...books].sort(...)`)
 * — and a caller that mutates a response in place would now leak that into
 * every other holder. Copy before mutating.
 */
const inFlight = new Map<string, Promise<unknown>>();

export function apiFetch<T = unknown>(path: string, init: RequestInit = {}, f?: Fetch): Promise<T> {
	// A load()'s own `fetch` bypasses the in-flight map: each page's fetch has to
	// SEE its own request to inline the response (see {@link Fetch}), and a
	// promise borrowed from another page's load — concurrent prerendering shares
	// this module — would leave this page hydrating from the network again.
	if (f) return requestJSON<T>(path, init, f);
	const method = (init.method ?? 'GET').toUpperCase();
	// Only GETs. A POST is an action, not a question — two of them are two
	// intentions, and collapsing them would drop one.
	if (method !== 'GET' || init.body || init.signal) {
		return requestJSON<T>(path, init);
	}
	const key = `${path}\u0000${tokenProvider() ?? ''}`;
	const existing = inFlight.get(key) as Promise<T> | undefined;
	if (existing) return existing;
	const request = requestJSON<T>(path, init).finally(() => inFlight.delete(key));
	inFlight.set(key, request);
	return request;
}

/**
 * Like {@link apiFetch} but returns the raw Response (with the Bearer token
 * attached) instead of parsing JSON — for downloads (CSV/blob) where a plain
 * `<a href>` can't carry the auth header.
 */
export async function apiFetchRaw(path: string, init: RequestInit = {}): Promise<Response> {
	const headers = new Headers(init.headers);
	const token = tokenProvider();
	if (token && !headers.has('Authorization')) {
		headers.set('Authorization', `Bearer ${token}`);
	}
	const res = await robustFetch(`${API_BASE_URL}${path}`, { ...init, headers });
	if (!res.ok) {
		throw new ApiError(res.status, await errorBody(res));
	}
	return res;
}
