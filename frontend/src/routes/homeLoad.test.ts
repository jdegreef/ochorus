import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { HomeShelves } from '$lib/homeShelves';

/**
 * The home page's two halves of one contract: the endpoint writes a snapshot
 * per locale at build time, and the page load reads it — loudly while
 * building, so an empty front page cannot ship looking deliberate, and
 * quietly at runtime, so an offline reader gets a shorter page, not an error.
 */
const env = vi.hoisted(() => ({ building: false }));
vi.mock('$app/environment', () => ({
	browser: true,
	dev: false,
	version: 'test',
	get building() {
		return env.building;
	}
}));
vi.mock('$lib/lang.svelte', () => ({ getLang: () => 'fr' }));
const homeShelves = vi.hoisted(() => vi.fn());
vi.mock('$lib/homeShelves', () => ({ homeShelves }));

const { load } = await import('./+page');
const { GET } = await import('./home-shelves/[lang].json/+server');

const SNAPSHOT: HomeShelves = {
	featured: [],
	authors: [{ slug: 'a', name: 'A', photo_url: '', book_count: 1 }],
	topics: [],
	counts: { books: 1, authors: 1, sermons: 0 }
};

// The load reads only `fetch`; the rest of the event is irrelevant to it.
const run = (fetch: typeof globalThis.fetch) =>
	(load as unknown as (e: { fetch: typeof fetch }) => Promise<HomeShelves>)({ fetch });

describe('home load', () => {
	beforeEach(() => {
		env.building = false;
	});

	it("reads the snapshot for the page's locale", async () => {
		const fetch = vi.fn(async () => Response.json(SNAPSHOT));
		expect(await run(fetch)).toEqual(SNAPSHOT);
		expect(fetch).toHaveBeenCalledWith('/home-shelves/fr.json');
	});

	it('degrades to empty shelves at runtime — a 404, or the SPA shell answering 200', async () => {
		const empty = { featured: [], authors: [], topics: [], counts: { books: 0, authors: 0, sermons: 0 } };
		expect(await run(async () => new Response('', { status: 404 }))).toEqual(empty);
		expect(await run(async () => new Response('<!doctype html>', { status: 200 }))).toEqual(empty);
	});

	it('fails the build instead of prerendering an empty front page', async () => {
		env.building = true;
		await expect(run(async () => new Response('', { status: 500 }))).rejects.toThrow(/500/);
	});
});

describe('home-shelves endpoint', () => {
	it("serves a registered locale's snapshot", async () => {
		homeShelves.mockResolvedValue(SNAPSHOT);
		const res = await GET({ params: { lang: 'fr' } } as Parameters<typeof GET>[0]);
		expect(await res.json()).toEqual(SNAPSHOT);
		expect(homeShelves).toHaveBeenCalledWith('fr');
	});

	it('404s an unknown locale rather than inventing an empty snapshot', async () => {
		await expect(GET({ params: { lang: 'xx' } } as Parameters<typeof GET>[0])).rejects.toMatchObject({
			status: 404
		});
	});
});
