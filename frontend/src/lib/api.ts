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
 * Fetch wrapper for the Django API. The library is public, so no auth header is
 * attached yet — Supabase Bearer tokens get added here when login lands.
 */
export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
	const headers = new Headers(init.headers);
	if (init.body && !headers.has('Content-Type')) {
		headers.set('Content-Type', 'application/json');
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
