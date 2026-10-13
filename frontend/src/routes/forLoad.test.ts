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
	getBook: vi.fn(),
	getSermon: vi.fn(),
	listSermons: vi.fn(),
	listAuthors: vi.fn(),
	getQuotePage: vi.fn()
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
		// A cached snapshot from before it was an object: a bare array of books.
		expect((await run('parents', async () => Response.json([{ slug: 'x' }]))).shelf).toEqual(EMPTY_SHELF_DATA);
	});

	it('fills in sections a cached snapshot from the last release lacks', async () => {
		const old = { shelves: [], plans: [], guides: [], offline: [] };
		expect((await run('parents', async () => Response.json(old))).shelf).toEqual(EMPTY_SHELF_DATA);
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
	const sermon = (slug: string, questions = 1) => ({
		slug,
		title: slug,
		scripture_ref: '',
		word_count: 2000,
		author_name: 'A',
		author_slug: 'a',
		study_questions: Array.from({ length: questions }, () => ({ question: 'Q', answer: 'A' }))
	});
	/** Every slug any page names, published — so each shelf fills. */
	const everything = () => [
		...new Set(FOR_PAGES.flatMap((p) => [...p.shelves.flatMap((s) => s.picks), ...(p.offline?.picks ?? [])]))
	];

	beforeEach(() => {
		// Not building: the build-wide memo of the shared lists would carry one
		// test's mock into the next.
		env.building = false;
		api.listBooks.mockResolvedValue(everything().map(book));
		api.listPlans.mockResolvedValue([...new Set(FOR_PAGES.flatMap((p) => p.plans))].map(plan));
		api.getAudienceShelf.mockImplementation(async (aud: string) => ({
			leader_guides: aud === 'young_readers' ? [book('g1'), book('g2')] : [book('g2'), book('g3')]
		}));
		api.getBook.mockImplementation(
			async (slug: string) => ({ ...book(slug), pdf_url: `/pdfs/${slug}.pdf`, epub_url: '' }) as unknown as BookDetail
		);
		api.listSermons.mockResolvedValue([{ slug: 's1' }, { slug: 's2' }]);
		api.getSermon.mockImplementation(async (slug: string) => sermon(slug));
		api.listAuthors.mockResolvedValue(
			[...new Set(FOR_PAGES.flatMap((p) => p.authors))].map((slug) => ({
				slug,
				name: slug,
				photo_url: '',
				birth_year: null,
				death_year: null,
				bio: 'long',
				has_long_bio: slug !== 'charles-h-spurgeon'
			}))
		);
		api.getQuotePage.mockImplementation(async (author: string) => ({
			author: { slug: author, name: author, photo_url: '', birth_year: null },
			topics: [],
			quotes: FOR_PAGES.filter((p) => p.quote.startsWith(author)).map((p) => ({
				slug: p.quote,
				text: 'A line.',
				paragraph: 1,
				source: { kind: 'chapter', slug: 'b', title: 'C', work: 'Book', order: 2, cover_color: '' }
			}))
		}));
	});

	it('serves the writers, the quotation and the numbers', async () => {
		const page = FOR_PAGES.find((p) => p.slug === 'churches')!;
		const got = await get('churches');
		// Spurgeon has no long bio in this mock, so the next writer takes his place.
		expect(got.authors.map((a) => a.slug)).toEqual(page.authors.filter((a) => a !== 'charles-h-spurgeon').slice(0, 6));
		expect(got.authors[0]).not.toHaveProperty('bio');
		expect(got.quote).toMatchObject({ slug: page.quote, text: 'A line.', author: { slug: expect.any(String) } });
		expect(got.counts).toEqual({ books: expect.any(Number), sermons: 2, plans: expect.any(Number) });
	});

	it('drops the numbers and the writers, not the build, when their lists fail', async () => {
		api.listSermons.mockRejectedValue(new Error('503'));
		api.listAuthors.mockRejectedValue(new Error('503'));
		const got = await get('youth');
		expect(got.authors).toEqual([]);
		expect(got.counts?.sermons).toBe(0);
		expect(got.shelves.length).toBeGreaterThan(0);
	});

	it('drops the quotation, not the build, when its quote page fails', async () => {
		api.getQuotePage.mockRejectedValue(new Error('404'));
		expect((await get('churches')).quote).toBeNull();
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

	it('serves an empty section rather than failing — the page falls back', async () => {
		// The churches page's main button jumps to #plans; forHref sends it to
		// /plans when the snapshot has none (CI's fixture API has few plans).
		api.listPlans.mockResolvedValue([]);
		expect((await get('churches')).plans).toEqual([]);
	});

	it('404s an unknown group rather than inventing a shelf', async () => {
		await expect(get('nobody')).rejects.toMatchObject({ status: 404 });
	});

	it('runs a sermon series a week per sermon with questions, skipping one without or one that fails', async () => {
		const [first, second, third, ...rest] = FOR_PAGES.find((p) => p.slug === 'small-groups')!.series![0].picks;
		api.getSermon.mockImplementation(async (slug: string) => {
			if (slug === second) throw new Error('404');
			return sermon(slug, slug === third ? 0 : 1);
		});
		const got = await get('small-groups');
		expect(got.series[0].sermons.map((w) => w.slug)).toEqual([first, ...rest].slice(0, 6));
		expect(got.series[0].sermons[0]).toMatchObject({ questions: 1, author: { name: 'A' } });
		expect((await get('youth')).series).toEqual([]);
	});

	it('shows three levels only where all three editions are published', async () => {
		const levels = FOR_PAGES.find((p) => p.slug === 'homeschool')!.levels!;
		const family = (b: string) => [`${b}-children`, `${b}-teens`, b];
		// The first work is missing its teens edition, so the next two show.
		api.listBooks.mockResolvedValue(
			[...everything(), ...levels.flatMap(family)].filter((s) => s !== `${levels[0]}-teens`).map(book)
		);
		const got = await get('homeschool');
		expect(got.levels.map((f) => f.map((r) => r.book.slug))).toEqual([family(levels[1]), family(levels[2])]);
		expect((await get('churches')).levels).toEqual([]);
	});

	it("lists every other live language from that language's own lists, only where the page asks", async () => {
		api.listBooks.mockImplementation(async (lang: string) =>
			lang === 'lg' ? [] : (lang === 'en' ? everything() : ['a-sw', 'b-sw']).map(book)
		);
		api.listSermons.mockImplementation(async (lang: string) => {
			if (lang === 'pt') throw new Error('503');
			return [{ slug: 's' }];
		});
		const got = await get('missionaries');
		const codes = got.languages.map((l) => l.code);
		// Luganda has no books in this mock, so it has no row; Portuguese's
		// sermons failing costs only its sermon count.
		expect(codes).not.toContain('lg');
		expect(codes).not.toContain('en');
		expect(got.languages.find((l) => l.code === 'pt')?.counts).toEqual({ books: 2, sermons: 0, plans: expect.any(Number) });
		expect(got.languages.find((l) => l.code === 'sw')).toMatchObject({ name: 'Swahili', counts: { books: 2, sermons: 1 } });
		api.listBooks.mockClear();
		expect((await get('churches')).languages).toEqual([]);
		expect(api.listBooks).toHaveBeenCalledTimes(1);
	});
});
