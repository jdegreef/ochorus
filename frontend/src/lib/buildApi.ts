/**
 * Which API the BUILD reads from — normally the one the site talks to, or a
 * throwaway local one (docs/build-without-prod-api.md).
 *
 * `OCHORUS_BUILD_API=local` makes the build prerender against an API it starts
 * itself from ../backend, seeded from this checkout (scripts/local-api.mjs),
 * instead of crawling production. PUBLIC_API_BASE_URL is NOT changed: it is
 * baked into the client bundle, the CSP and the URLs SvelteKit keys each
 * inlined response by, and all three must keep naming production — a page
 * whose inlined `fetch` was keyed `http://127.0.0.1:…` would refetch every
 * response from the live API on hydration. So only the build's own network
 * request is retargeted (hooks.server.ts), and the inlined key stays put.
 *
 * Unset, everything here is inert: `localBuildApiOrigin` is null and the build
 * behaves exactly as it always has.
 *
 * Plain TS with no SvelteKit imports, so the node scripts can import it too.
 */

/** The default port: away from 8000, which a developer's runserver holds. */
export const DEFAULT_LOCAL_API_PORT = 8765;

type Env = Record<string, string | undefined>;

/** `http://127.0.0.1:<port>` in local-API mode, else null. */
export function localBuildApiOrigin(env: Env): string | null {
	if ((env.OCHORUS_BUILD_API || '').trim().toLowerCase() !== 'local') return null;
	const raw = (env.OCHORUS_BUILD_API_PORT || '').trim();
	const port = raw ? Number(raw) : DEFAULT_LOCAL_API_PORT;
	if (!Number.isInteger(port) || port < 1 || port > 65535) {
		throw new Error(`OCHORUS_BUILD_API_PORT must be a port number, got ${JSON.stringify(raw)}`);
	}
	return `http://127.0.0.1:${port}`;
}

/** The base URL build-time scripts should call: the local API, else PUBLIC_API_BASE_URL. */
export function buildApiBase(env: Env): string {
	return (localBuildApiOrigin(env) ?? env.PUBLIC_API_BASE_URL ?? '').replace(/\/+$/, '');
}

/**
 * `input` addressed to `to` instead of `from` when it is addressed to `from`;
 * otherwise `input` itself. Path, query and — for a Request — method, headers
 * and signal are kept. Takes every form `fetch` does: the build's chain calls
 * it with Requests (load's fetch) and with URL strings (the chapter batcher,
 * through apiFetch).
 */
export function retarget<T extends string | URL | Request>(input: T, from: string, to: string): T {
	const raw = input instanceof Request ? input.url : String(input);
	if (!URL.canParse(raw)) return input; // a relative path is never the API's
	const url = new URL(raw);
	if (url.origin !== from) return input;
	const target = new URL(url.pathname + url.search, to);
	if (input instanceof Request) return new Request(target, input) as T;
	return (typeof input === 'string' ? target.href : target) as T;
}
