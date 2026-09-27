/**
 * How the web build's load `fetch`es reach the API (wired in hooks.server.ts):
 * chapters from their batched run ($lib/chapterBatch), then a repeated request
 * from the first answer, then the API.
 *
 * Repeats are safe to answer from memory because the API can't change under
 * one build, and they are common: each language's book, author and article
 * lists are asked for by a dozen pages apiece. A cached answer is the same
 * bytes, status and statusText — all SvelteKit inlines — so every page is
 * byte-identical to one built from its own request. Only 200s and 404s are kept
 * (a 404 is a real answer the English fallback keys on); a 5xx always reaches
 * the caller, so the build's retries still see it.
 */

import { isAnonymousApiGet, type Fetch } from './api';
import { createChapterBatcher } from './chapterBatch';

type Entry = { body: ArrayBuffer; status: number; statusText: string; contentType: string };

/** Bodies held at most. Only repeated URLs are stored, a few MB in practice. */
const MAX_BYTES = 64 * 1024 * 1024;

export function createResponseCache(apiOrigin: string, maxBytes = MAX_BYTES) {
	// Stored on the SECOND request for a URL: most of the crawl's requests are
	// one-off pages, and those pass straight through without being copied.
	const seen = new Set<string>();
	const entries = new Map<string, Entry>();
	let bytes = 0;

	const toResponse = (e: Entry) =>
		new Response(e.body, {
			status: e.status,
			statusText: e.statusText,
			headers: { 'content-type': e.contentType }
		});

	return async function cachedFetch(request: Request, fetch: Fetch): Promise<Response> {
		if (!isAnonymousApiGet(request, apiOrigin)) return fetch(request);
		const key = request.url;
		const hit = entries.get(key);
		if (hit) return toResponse(hit);

		const response = await fetch(request);
		const keep = response.status === 200 || response.status === 404;
		if (!keep || !seen.has(key)) {
			seen.add(key);
			return response;
		}
		const entry: Entry = {
			body: await response.arrayBuffer(),
			status: response.status,
			statusText: response.statusText,
			contentType: response.headers.get('content-type') ?? 'application/json'
		};
		if (bytes + entry.body.byteLength <= maxBytes) {
			entries.set(key, entry);
			bytes += entry.body.byteLength;
		}
		return toResponse(entry);
	};
}

/** The build's fetch chain: chapter batch, then response cache, then the API. */
export function createBuildFetch(apiOrigin: string) {
	const chapterFromBatch = createChapterBatcher(apiOrigin);
	const cachedFetch = createResponseCache(apiOrigin);
	return async (request: Request, fetch: Fetch): Promise<Response> =>
		(await chapterFromBatch(request, fetch)) ?? cachedFetch(request, fetch);
}
