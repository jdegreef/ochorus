/**
 * The two halves of $lib/chapterSeed that only the build exercises: the load's
 * seed lookup must not touch `document` outside the browser, and a chapter read
 * through `unrecorded` must not be inlined by SvelteKit's own load fetch. The
 * second runs the real `create_universal_fetch` (a SvelteKit internal, which is
 * the point): if an upgrade starts recording clones, the prose ships twice on
 * every chapter page again, and this fails instead of the pages silently growing.
 */
import { describe, expect, it, vi } from 'vitest';

// A compile-time constant SvelteKit's Vite plugin defines; the internal reads it.
vi.hoisted(() => {
	(globalThis as Record<string, unknown>).__SVELTEKIT_SERVER_TRACING_ENABLED__ = false;
});
vi.mock('$app/environment', () => ({ browser: false, dev: false, building: true, version: 'test' }));

import { chapterFetch, takeChapterSeed, unrecorded } from './chapterSeed';
// @ts-expect-error — an untyped internal module, imported by path on purpose.
import { create_universal_fetch } from '../../node_modules/@sveltejs/kit/src/runtime/server/page/load_data.js';

type Fetched = { url: string; response_body?: string };

const BODY = '{"order":3,"body_html":"<p>prose</p>"}';
const API = 'https://api.ochorus.com/api/library/books/humility/chapters/3/?language=en';

/** A load's `fetch` as SvelteKit builds it for a prerendered page, and the
 *  list of responses it would inline into that page. */
function loadFetch() {
	const fetched: Fetched[] = [];
	const event = {
		url: new URL('https://ochorus.com/books/humility/3/'),
		request: new Request('https://ochorus.com/books/humility/3/'),
		route: { id: '/books/[slug]/[order]' },
		fetch: async () =>
			new Response(BODY, {
				headers: { 'content-type': 'application/json', 'access-control-allow-origin': '*' }
			})
	};
	const f = create_universal_fetch(event, {}, fetched, true, {
		filterSerializedResponseHeaders: () => false
	}) as typeof fetch;
	return { f, fetched };
}

describe('the build side of the chapter seed', () => {
	it('never reads the DOM outside the browser', () => {
		vi.stubGlobal('document', undefined);
		try {
			expect(takeChapterSeed('/books/humility/3/')).toBeNull();
		} finally {
			vi.unstubAllGlobals();
		}
	});

	it('SvelteKit inlines a response its load fetch sees read (the control)', async () => {
		const { f, fetched } = loadFetch();
		await (await f(API)).json();
		expect(fetched.map((r) => r.response_body)).toEqual([BODY]);
	});

	it('and inlines nothing read through unrecorded — the body ships once', async () => {
		const { f, fetched } = loadFetch();
		expect(await (await unrecorded(f)(API)).json()).toEqual(JSON.parse(BODY));
		expect(fetched).toEqual([]);
	});

	it('is what a chapter load reads with in the build', async () => {
		const { f, fetched } = loadFetch();
		await (await chapterFetch(f)(API)).json();
		expect(fetched).toEqual([]);
	});
});
