import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { BookSummary, CoverBook } from '$lib/library-public';

/**
 * The "Ochorus for …" pages' two halves of one contract, on the home page's
 * model (homeLoad.test.ts): the endpoint writes each page's starter shelf at
 * build time, and the page load reads it — loudly while building, quietly at
 * runtime.
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
const listBooks = vi.hoisted(() => vi.fn());
vi.mock('$lib/library-public', async (orig) => ({
	...(await orig<typeof import('$lib/library-public')>()),
	listBooks
}));

const { load } = await import('./for/[group]/+page');
const { GET } = await import('./for-shelves/[group].json/+server');

const SHELF = [{ slug: 'school-of-prayer' }] as CoverBook[];

type LoadResult = { page: { slug: string }; books: CoverBook[] };
const run = (group: string, fetch: typeof globalThis.fetch) =>
	(load as unknown as (e: { params: { group: string }; fetch: typeof fetch }) => Promise<LoadResult>)({
		params: { group },
		fetch
	});
const get = (group: string) =>
	GET({ params: { group }, fetch } as unknown as Parameters<typeof GET>[0]);

describe('"Ochorus for" load', () => {
	beforeEach(() => {
		env.building = false;
	});

	it("reads the page's shelf snapshot", async () => {
		const fetch = vi.fn(async () => Response.json(SHELF));
		const got = await run('churches', fetch);
		expect(got.page.slug).toBe('churches');
		expect(got.books).toEqual(SHELF);
		expect(fetch).toHaveBeenCalledWith('/for-shelves/churches.json');
	});

	it('404s a group with no page', async () => {
		await expect(run('nobody', vi.fn())).rejects.toMatchObject({ status: 404 });
	});

	it('drops the shelf at runtime — a 404, or the SPA shell answering 200', async () => {
		expect((await run('parents', async () => new Response('', { status: 404 }))).books).toEqual([]);
		expect((await run('parents', async () => new Response('<!doctype html>'))).books).toEqual([]);
	});

	it('fails the build instead of prerendering a page without its books', async () => {
		env.building = true;
		await expect(run('parents', async () => new Response('', { status: 500 }))).rejects.toThrow(/500/);
	});
});

describe('for-shelves endpoint', () => {
	const book = (slug: string) =>
		({ slug, language: 'en', title: slug, author: { slug: 'a', name: 'A', birth_year: null } }) as unknown as BookSummary;

	it("serves the page's published picks, in its order", async () => {
		listBooks.mockResolvedValue([book('power-through-prayer'), book('school-of-prayer'), book('other')]);
		const res = await get('churches');
		expect((await res.json()).map((b: CoverBook) => b.slug)).toEqual(['school-of-prayer', 'power-through-prayer']);
		expect(listBooks).toHaveBeenCalledWith('en', expect.anything());
	});

	it('fails rather than serving an empty shelf', async () => {
		listBooks.mockResolvedValue([book('other')]);
		await expect(get('churches')).rejects.toMatchObject({ status: 500 });
	});

	it('404s an unknown group rather than inventing a shelf', async () => {
		await expect(get('nobody')).rejects.toMatchObject({ status: 404 });
	});
});
