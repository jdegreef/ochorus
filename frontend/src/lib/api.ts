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

	const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
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
	const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
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
