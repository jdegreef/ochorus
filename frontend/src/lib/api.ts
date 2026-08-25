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

async function robustFetch(url: string, init: RequestInit): Promise<Response> {
	if (!building || !isIdempotent(init)) return fetch(url, init);
	for (let attempt = 0; ; attempt++) {
		const outOfRetries = attempt >= BUILD_RETRY_DELAYS_MS.length;
		let failure: string;
		try {
			const res = await fetch(url, init);
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
async function requestJSON<T>(path: string, init: RequestInit): Promise<T> {
	const headers = new Headers(init.headers);
	if (init.body && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}
	const token = tokenProvider();
	if (token && !headers.has('Authorization')) {
		headers.set('Authorization', `Bearer ${token}`);
	}

	const res = await robustFetch(`${API_BASE_URL}${path}`, {
		...init,
		headers,
		signal: withTimeout(init.signal)
	});
	if (!res.ok) {
		let body: unknown = null;
		try {
			body = await res.json();
		} catch {
			body = await res.text().catch(() => null);
		}
		throw new ApiError(res.status, body);
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

function withTimeout(caller: AbortSignal | null | undefined): AbortSignal | undefined {
	if (building) return caller ?? undefined;
	const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
	// Preserve a caller's own signal (the define popover aborts on new input).
	return caller ? AbortSignal.any([caller, timeout]) : timeout;
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

export function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
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
		// Parse the error body as JSON when possible (DRF errors are JSON) so
		// callers can read `.detail`, matching apiFetch; fall back to raw text.
		let body: unknown = null;
		try {
			body = await res.json();
		} catch {
			body = await res.text().catch(() => null);
		}
		throw new ApiError(res.status, body);
	}
	return res;
}
