/**
 * Prerender chapter pages from batched API responses: the build's `handleFetch`
 * answers each chapter page's request from a run of chapters fetched in one
 * request (`/api/library/books/<slug>/chapters/?from=&limit=`).
 *
 * The page still asks for its own URL through load's `fetch` and gets the same
 * JSON the API would send. That matters: SvelteKit inlines the response into
 * the page and hydration replays it by URL, so the reader's browser makes no
 * request the old page didn't. Anything unexpected — a failed or 404 batch, a
 * chapter missing from its run — falls through to the real request.
 */

import type { Fetch } from './api';
import { getChapterRun } from './library-public';

/** Must not exceed the API's CHAPTER_BATCH_MAX (library/views.py). */
export const CHAPTER_BATCH_SIZE = 25;

/**
 * Runs held at once. The crawl takes a book's chapters roughly in order, so a
 * run is normally used up before the next is fetched; the cap only bounds the
 * worst case (a crawl that interleaves many books) at about 40 MB of JSON. An
 * evicted run is simply fetched again if its chapters are still to come.
 */
const MAX_RUNS = 40;

const CHAPTER_PATH = /^\/api\/library\/books\/([^/]+)\/chapters\/(\d+)\/$/;

type Run = Map<number, unknown>;

export function createChapterBatcher(apiOrigin: string) {
	// key → the run's chapters by order, or null when the batch failed (the
	// run's pages then take the per-chapter path; retrying the batch for each
	// of them would only add requests while the API is struggling).
	const runs = new Map<string, Promise<Run | null>>();

	function fetchRun(key: string, slug: string, language: string, from: number, fetch: Fetch) {
		let run = runs.get(key);
		if (!run) {
			// Through apiFetch, so a transient 5xx or network error gets the same
			// build-time retries as a per-chapter request before the run is given up.
			run = getChapterRun(slug, language, from, CHAPTER_BATCH_SIZE, fetch)
				.then((chapters) => new Map<number, unknown>(chapters.map((c) => [c.order, c])))
				.catch(() => null);
			runs.set(key, run);
			while (runs.size > MAX_RUNS) runs.delete(runs.keys().next().value!);
		}
		return run;
	}

	/**
	 * The response for a chapter request, answered from its run — or null when
	 * the request isn't a chapter request, or the run can't answer it, and the
	 * caller should make the real request.
	 */
	return async function chapterFromBatch(request: Request, fetch: Fetch): Promise<Response | null> {
		if (request.method !== 'GET') return null;
		const url = new URL(request.url);
		if (url.origin !== apiOrigin) return null;
		const match = CHAPTER_PATH.exec(url.pathname);
		if (!match) return null;
		// Only the query the chapter page sends. Anything else is a request this
		// batcher doesn't understand, so it goes to the API untouched.
		const language = url.searchParams.get('language');
		if (!language || [...url.searchParams.keys()].some((k) => k !== 'language')) return null;

		const [, slug, orderText] = match;
		const order = Number(orderText);
		const from = Math.floor((order - 1) / CHAPTER_BATCH_SIZE) * CHAPTER_BATCH_SIZE + 1;
		const key = `${slug}|${language}|${from}`;

		const pending = fetchRun(key, slug, language, from, fetch);
		const run = await pending;
		const chapter = run?.get(order);
		if (!run || chapter === undefined) return null;
		// Each chapter page is built once, so hand its chapter over and let the
		// run shrink; an empty run is dropped. A second request for the same
		// chapter (a retry) takes the per-chapter path.
		run.delete(order);
		// Only if the map still holds THIS run: an evicted run that was fetched
		// again lives under the same key, and its chapters are still to come.
		if (run.size === 0 && runs.get(key) === pending) runs.delete(key);
		// statusText too: SvelteKit inlines it with the body, and the page should
		// be byte-identical to one built from the per-chapter request.
		return new Response(JSON.stringify(chapter), {
			status: 200,
			statusText: 'OK',
			headers: { 'content-type': 'application/json' }
		});
	};
}
