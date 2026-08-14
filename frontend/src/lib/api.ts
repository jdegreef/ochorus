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
export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
	const headers = new Headers(init.headers);
	if (init.body && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
	}
	const token = tokenProvider();
	if (token && !headers.has('Authorization')) {
		headers.set('Authorization', `Bearer ${token}`);
	}

	const res = await robustFetch(`${API_BASE_URL}${path}`, { ...init, headers });
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
