import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EMPTY_SHELF_DATA, FOR_PAGES, type ForShelfData } from '$lib/forPages';
import type { BookDetail, BookSummary, PlanSummary } from '$lib/library-public';

/**
 * The "Ochorus for …" pages' two halves of one contract, on the home page's
 * model (homeLoad.test.ts): the endpoint writes each page's shelves, plans,
 * guides and offline pack at build time, and the page load reads them —
 * loudly while building, quietly at runtime.
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
const api = vi.hoisted(() => ({
	listBooks: vi.fn(),
	listPlans: vi.fn(),
	getAudienceShelf: vi.fn(),
	getBook: vi.fn()
}));
vi.mock('$lib/library-public', async (orig) => ({
	...(await orig<typeof import('$lib/library-public')>()),
	...api
}));

const { load } = await import('./for/[group]/+page');
const { GET } = await import('./for-shelves/[group].json/+server');

const SNAPSHOT: ForShelfData = { ...EMPTY_SHELF_DATA, shelves: [{ title: 'T', note: 'N', books: [] }] };

type LoadResult = { page: { slug: string }; shelf: ForShelfData };
const run = (group: string, fetch: typeof globalThis.fetch) =>
	(load as unknown as (e: { params: { group: string }; fetch: typeof fetch }) => Promise<LoadResult>)({
		params: { group },
		fetch
	});
const get = async (group: string) =>
	(await (await GET({ params: { group }, fetch } as unknown as Parameters<typeof GET>[0])).json()) as ForShelfData;

describe('"Ochorus for" load', () => {
	beforeEach(() => {
		env.building = false;
	});

	it("reads the page's snapshot", async () => {
		const fetch = vi.fn(async () => Response.json(SNAPSHOT));
		const got = await run('churches', fetch);
		expect(got.page.slug).toBe('churches');
		expect(got.shelf).toEqual(SNAPSHOT);
		expect(fetch).toHaveBeenCalledWith('/for-shelves/churches.json');
	});

	it('404s a group with no page', async () => {
		await expect(run('nobody', vi.fn())).rejects.toMatchObject({ status: 404 });
	});

	it('drops the sections at runtime — a 404, or the SPA shell answering 200', async () => {
		expect((await run('parents', async () => new Response('', { status: 404 }))).shelf).toEqual(EMPTY_SHELF_DATA);
		expect((await run('parents', async () => new Response('<!doctype html>'))).shelf).toEqual(EMPTY_SHELF_DATA);
	});

	it('fails the build instead of prerendering a page without its books', async () => {
		env.building = true;
		await expect(run('parents', async () => new Response('', { status: 500 }))).rejects.toThrow(/500/);
	});
});

describe('for-shelves endpoint', () => {
	const book = (slug: string) =>
		({ slug, language: 'en', title: slug, author: { slug: 'a', name: 'A', birth_year: null } }) as unknown as BookSummary;
	const plan = (slug: string) => ({ slug }) as PlanSummary;
	/** Every slug any page names, published — so each shelf fills. */
	const everything = () => [
		...new Set(FOR_PAGES.flatMap((p) => [...p.shelves.flatMap((s) => s.picks), ...(p.offline?.picks ?? [])]))
	];

	beforeEach(() => {
		api.listBooks.mockResolvedValue(everything().map(book));
		api.listPlans.mockResolvedValue([...new Set(FOR_PAGES.flatMap((p) => p.plans))].map(plan));
		api.getAudienceShelf.mockImplementation(async (aud: string) => ({
			leader_guides: aud === 'young_readers' ? [book('g1'), book('g2')] : [book('g2'), book('g3')]
		}));
		api.getBook.mockImplementation(
			async (slug: string) => ({ ...book(slug), pdf_url: `/pdfs/${slug}.pdf`, epub_url: '' }) as unknown as BookDetail
		);
	});

	it("serves each shelf's published picks, in its order and capped", async () => {
		api.listBooks.mockResolvedValue(['the-way-to-god', 'school-of-prayer', 'other', ...everything()].map(book));
		const got = await get('churches');
		const page = FOR_PAGES.find((p) => p.slug === 'churches')!;
		expect(got.shelves.map((s) => s.title)).toEqual(page.shelves.map((s) => s.title));
		expect(got.shelves[0].books.slice(0, 2).map((b) => b.slug)).toEqual(['school-of-prayer', 'the-way-to-god']);
		expect(api.listBooks).toHaveBeenCalledWith('en', expect.anything());
	});

	it("serves the page's plans in its order", async () => {
		const got = await get('churches');
		expect(got.plans.map((p) => p.slug)).toEqual(['grace-for-every-sinner', 'new-to-the-faith', 'school-of-prayer']);
	});

	it('serves the leader’s guides once each, children’s hub first — only where the page asks', async () => {
		expect((await get('homeschool')).guides.map((b) => b.slug)).toEqual(['g1', 'g2', 'g3']);
		api.getAudienceShelf.mockClear();
		expect((await get('missionaries')).guides).toEqual([]);
		expect(api.getAudienceShelf).not.toHaveBeenCalled();
	});

	it('packs the offline books that have a download, skipping unpublished and file-less ones', async () => {
		const [first, second, third] = FOR_PAGES.find((p) => p.slug === 'missionaries')!.offline!.picks;
		api.listBooks.mockResolvedValue(everything().filter((s) => s !== first).map(book));
		api.getBook.mockImplementation(
			async (slug: string) =>
				({ ...book(slug), pdf_url: slug === second ? '' : `/pdfs/${slug}.pdf`, epub_url: '' }) as unknown as BookDetail
		);
		const got = await get('missionaries');
		expect(api.getBook).not.toHaveBeenCalledWith(first, 'en', expect.anything());
		expect(got.offline.map((o) => o.book.slug)).not.toContain(second);
		expect(got.offline[0]).toMatchObject({ book: { slug: third }, pdf_url: `/pdfs/${third}.pdf` });
	});

	it('fails rather than serving an empty shelf', async () => {
		api.listBooks.mockResolvedValue([book('other')]);
		await expect(get('churches')).rejects.toMatchObject({ status: 500 });
	});

	it('fails rather than shipping a button to an empty section', async () => {
		api.listPlans.mockResolvedValue([]);
		// The churches page's main button jumps to #plans.
		await expect(get('churches')).rejects.toMatchObject({ status: 500 });
	});

	it('404s an unknown group rather than inventing a shelf', async () => {
		await expect(get('nobody')).rejects.toMatchObject({ status: 404 });
	});
});
