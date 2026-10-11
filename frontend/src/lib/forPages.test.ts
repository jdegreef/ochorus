import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { FOR_LINKS, forPath } from './forLinks';
import { messageShareLinks } from './share';
import {
	AUTHORS_SHOWN,
	countWorks,
	EMPTY_SHELF_DATA,
	forQuote,
	inviteMessage,
	quoteAuthor,
	FOR_PAGES,
	PLANS_SHOWN,
	forHref,
	isShelfData,
	type ForAnchor,
	isForAnchor,
	pageLinks,
	SHELF_SIZE,
	forPage,
	forPlans,
	forShelf,
	countsLine,
	forLanguage,
	forLevels,
	LANGUAGE_COVERS,
	LEVELS_SHOWN,
	SERIES_WEEKS,
	toForSermon,
	toOfflineBook
} from './forPages';
import type { BookDetail, BookSummary, PlanSummary, QuotePage } from './library-public';

const ROUTES = join(import.meta.dirname, '..', 'routes');
const LIBRARY = join(import.meta.dirname, '..', '..', '..', 'backend', 'library');
const BOOKS = join(LIBRARY, 'fixtures', 'content', 'books');
/** The quote seed and the authors fixture, read as text / JSON. */
const QUOTE_SEED = readFileSync(join(LIBRARY, 'quote_seed.py'), 'utf8');
const APPROVED = new Set(
	[...(/APPROVED = frozenset\(\s*\{([^}]*)\}/.exec(QUOTE_SEED)?.[1] ?? '').matchAll(/"([a-z0-9-]+)"/g)].map((m) => m[1])
);
const AUTHOR_SLUGS = new Set(
	(JSON.parse(readFileSync(join(LIBRARY, 'fixtures', 'content', 'authors.json'), 'utf8')) as { fields: { slug: string } }[]).map(
		(r) => r.fields.slug
	)
);
/** The plan slugs in the seed: each plan tuple's FIRST element (the rest of the
 *  tuple names its source books, which must not count; comment lines may sit
 *  between the parenthesis and it). */
const PLAN_SLUGS = new Set(
	[...readFileSync(join(LIBRARY, 'plan_seed.py'), 'utf8').matchAll(/\(\s*\n(?:\s*#[^\n]*\n)*\s*"([a-z0-9-]+)",/g)].map((m) => m[1])
);

/** This slug's English book row in the content fixture, or null. */
const fixtureBook = (slug: string): { is_published: boolean; pdf_url: string } | null => {
	try {
		return JSON.parse(readFileSync(join(BOOKS, `${slug}.en.json`), 'utf8'))[0].fields;
	} catch {
		return null;
	}
};

/** This slug's English sermon row in the content fixture, or null. */
const fixtureSermon = (slug: string): { study_questions: unknown[] } | null => {
	try {
		return JSON.parse(readFileSync(join(LIBRARY, 'fixtures', 'content', 'sermons', `${slug}.en.json`), 'utf8'))[0].fields;
	} catch {
		return null;
	}
};

/** Is this slug a published English book in the content fixture? */
const publishedInFixture = (slug: string) => fixtureBook(slug)?.is_published === true;

/** Does an unlocalized internal path name a real route directory? */
const routeExists = (href: string) => {
	const [first] = href.replace(/^\//, '').split('/');
	return readdirSync(ROUTES).includes(first);
};

describe('the "Ochorus for …" pages', () => {
	it('has one page per footer link, in the same order', () => {
		expect(FOR_PAGES.map((p) => p.slug)).toEqual(FOR_LINKS.map((l) => l.slug));
	});

	it('looks pages up by slug', () => {
		expect(forPage('churches')?.slug).toBe('churches');
		expect(forPage('nobody')).toBeUndefined();
		expect(forPath('parents')).toBe('/for/parents/');
	});

	it('links only to routes that exist, or to a section the page has', () => {
		for (const p of FOR_PAGES) {
			const has: Record<ForAnchor, boolean> = {
				'#plans': p.plans.length > 0,
				'#shelves': p.shelves.length > 0,
				'#guides': !!p.guides,
				'#offline': !!p.offline,
				'#languages': !!p.languages,
				'#series': !!p.series?.length
			};
			for (const href of pageLinks(p)) {
				if (href.startsWith('#')) {
					expect(isForAnchor(href), `${p.slug}: ${href}`).toBe(true);
					expect(has[href as ForAnchor], `${p.slug} links ${href} but has no such section`).toBe(true);
					continue;
				}
				expect(href, `${p.slug}: ${href}`).toMatch(/^\/[a-z-]+$/);
				expect(routeExists(href), `${p.slug}: ${href}`).toBe(true);
			}
		}
	});

	it('gives every page enough to say, without repeats', () => {
		for (const p of FOR_PAGES) {
			expect(p.points.length, p.slug).toBeGreaterThanOrEqual(3);
			expect(p.ideas.length, p.slug).toBeGreaterThanOrEqual(3);
			// Two or more, or pickQa drops the FAQPage block.
			expect(p.questions.length, p.slug).toBeGreaterThanOrEqual(2);
			expect(p.shelves.length, p.slug).toBeGreaterThanOrEqual(2);
			// No book on two of a page's shelves (the offline pack may repeat them).
			const shelved = p.shelves.flatMap((x) => x.picks);
			expect(new Set(shelved).size, `${p.slug}: a book is on two shelves`).toBe(shelved.length);
			for (const x of p.shelves) {
				// Backups beyond the row, so one unpublished pick leaves no gap.
				expect(x.picks.length, `${p.slug} / ${x.title}`).toBeGreaterThan(SHELF_SIZE);
			}
			expect(new Set(p.plans).size, p.slug).toBe(p.plans.length);
			expect(p.plans.length, p.slug).toBeGreaterThan(PLANS_SHOWN);
			if (p.offline) expect(new Set(p.offline.picks).size, p.slug).toBe(p.offline.picks.length);
			expect(p.seoDescription.length, p.slug).toBeLessThanOrEqual(160);
		}
	});

	it('picks books that exist, so a renamed or unpublished pick is caught here', () => {
		// The fixture is not prod's word on what is published (is_published is
		// create-only in the seed), but it is CI's — and a slug missing from it
		// is a typo or a rename.
		for (const p of FOR_PAGES) {
			const picks = [...p.shelves.flatMap((x) => x.picks), ...(p.offline?.picks ?? [])];
			expect(picks.filter((s) => !publishedInFixture(s)), p.slug).toEqual([]);
		}
	});

	it('picks plans the seed defines', () => {
		// The parse itself: a plan slug counts, a source book's does not.
		expect(PLAN_SLUGS.has('humility-12-days')).toBe(true);
		expect(PLAN_SLUGS.has('humility-2')).toBe(false);
		for (const p of FOR_PAGES) {
			expect(p.plans.filter((s) => !PLAN_SLUGS.has(s)), p.slug).toEqual([]);
		}
	});

	it('packs only books with a download, so an offline pick never silently drops', () => {
		for (const p of FOR_PAGES) {
			// The fixture's pdf_url is the PDF the book page offers (export_policy
			// lists the edition, book-pdfs.yml builds the file).
			const missing = (p.offline?.picks ?? []).filter((s) => !fixtureBook(s)?.pdf_url);
			expect(missing, p.slug).toEqual([]);
		}
	});

	it('takes the picks in the page order, drops missing ones, and caps the shelf', () => {
		const book = (slug: string) =>
			({ slug, language: 'en', title: slug, author: { slug: 'a', name: 'A', birth_year: null } }) as unknown as BookSummary;
		const all = [book('b'), book('a'), book('c')];
		expect(forShelf(all, ['a', 'missing', 'b']).map((b) => b.slug)).toEqual(['a', 'b']);
		const many = Array.from({ length: SHELF_SIZE + 2 }, (_, i) => book(`b${i}`));
		expect(forShelf(many, many.map((b) => b.slug))).toHaveLength(SHELF_SIZE);
	});

	it('takes the plans in the page order, drops missing ones, and caps the row', () => {
		const plan = (slug: string) => ({ slug }) as PlanSummary;
		const all = ['a', 'b', 'c', 'd', 'e'].map(plan);
		expect(forPlans(all, ['c', 'missing', 'a']).map((p) => p.slug)).toEqual(['c', 'a']);
		expect(forPlans(all, ['a', 'b', 'c', 'd', 'e'])).toHaveLength(PLANS_SHOWN);
	});

	it('packs a book only when it has a file to download', () => {
		const detail = (pdf: string, epub?: string) =>
			({
				slug: 'x',
				language: 'en',
				title: 'X',
				author: { slug: 'a', name: 'A', birth_year: null },
				pdf_url: pdf,
				epub_url: epub
			}) as unknown as BookDetail;
		expect(toOfflineBook(detail('', ''))).toBeNull();
		expect(toOfflineBook(detail(''))).toBeNull();
		expect(toOfflineBook(detail('/pdfs/x.pdf'))).toMatchObject({ pdf_url: '/pdfs/x.pdf', epub_url: '' });
		expect(toOfflineBook(detail('', '/api/x.epub'))?.book.slug).toBe('x');
	});

	it('sends an anchor whose section is missing to the page that holds the same things', () => {
		const plans = [{ slug: 'p' }] as PlanSummary[];
		expect(forHref('#plans', { ...EMPTY_SHELF_DATA, plans })).toBe('#plans');
		expect(forHref('#plans', EMPTY_SHELF_DATA)).toBe('/plans');
		expect(forHref('#offline', EMPTY_SHELF_DATA)).toBe('/books');
		expect(forHref('#series', EMPTY_SHELF_DATA)).toBe('/sermons');
		expect(forHref('/teens', EMPTY_SHELF_DATA)).toBe('/teens');
	});

	it('knows a snapshot from anything else', () => {
		expect(isShelfData(EMPTY_SHELF_DATA)).toBe(true);
		expect(isShelfData([{ slug: 'school-of-prayer' }])).toBe(false);
		expect(isShelfData(null)).toBe(false);
		expect(isShelfData({})).toBe(false);
		// A cached snapshot from before a section existed: the load fills it in.
		expect(isShelfData({ shelves: [], plans: [], guides: [], offline: [] })).toBe(true);
		expect(isShelfData({ ...EMPTY_SHELF_DATA, series: {} })).toBe(false);
	});

	it('quotes a line the seed holds, from an author whose quotations are approved', () => {
		expect(APPROVED.size, 'the APPROVED parse found nothing').toBeGreaterThan(3);
		for (const p of FOR_PAGES) {
			expect(QUOTE_SEED.includes(`"slug": "${p.quote}"`), `${p.slug}: ${p.quote}`).toBe(true);
			expect(APPROVED.has(quoteAuthor(p.quote)), `${p.slug}: ${quoteAuthor(p.quote)} is not approved`).toBe(true);
		}
	});

	it('names writers who exist, with backups beyond the grid', () => {
		for (const p of FOR_PAGES) {
			expect(p.authors.filter((a) => !AUTHOR_SLUGS.has(a)), p.slug).toEqual([]);
			expect(new Set(p.authors).size, p.slug).toBe(p.authors.length);
			expect(p.authors.length, p.slug).toBeGreaterThan(AUTHORS_SHOWN);
		}
	});

	it('invites readers to a page that exists, in a message short enough to paste anywhere', () => {
		for (const p of FOR_PAGES) {
			expect(p.invite.href === '/' || routeExists(p.invite.href), `${p.slug}: ${p.invite.href}`).toBe(true);
			expect(p.invite.text.length, p.slug).toBeLessThanOrEqual(200);
		}
		const msg = inviteMessage({ text: 'Read with us.', href: '/young-readers' }, 'https://x.org');
		expect(msg).toBe('Read with us.\nhttps://x.org/young-readers/');
		const [whatsapp, email] = messageShareLinks('Subject', msg, 'Email');
		expect(whatsapp.href).toBe(`https://wa.me/?text=${encodeURIComponent(msg)}`);
		expect(email.href).toContain(`body=${encodeURIComponent(msg)}`);
	});

	it('resolves a quotation from its author’s page, or nothing', () => {
		expect(quoteAuthor('charles-h-spurgeon-116882b5')).toBe('charles-h-spurgeon');
		const page = {
			author: { slug: 'a', name: 'A', photo_url: '', birth_year: null },
			topics: [],
			quotes: [
				{ slug: 'a-12345678', text: 'Grace.', paragraph: 3, source: { kind: 'chapter', slug: 'b', title: 'C', work: 'Book', order: 2, cover_color: '' } }
			]
		} as QuotePage;
		expect(forQuote(page, 'a-12345678')).toMatchObject({ slug: 'a-12345678', text: 'Grace.', author: { slug: 'a', name: 'A' } });
		expect(forQuote(page, 'a-00000000')).toBeNull();
	});

	it('counts works, not their young-reader editions', () => {
		const slugs = ['pilgrims-progress', 'pilgrims-progress-teens', 'pilgrims-progress-children', 'confessions'];
		expect(countWorks(slugs.map((slug) => ({ slug })))).toBe(2);
	});

	it('builds each sermon series from sermons with study questions, with backups', () => {
		for (const p of FOR_PAGES) {
			for (const series of p.series ?? []) {
				const ok = series.picks.filter((s) => fixtureSermon(s)?.study_questions.length);
				expect(ok, `${p.slug}: ${series.title}`).toEqual(series.picks);
				expect(new Set(series.picks).size, series.title).toBe(series.picks.length);
				expect(series.picks.length, series.title).toBeGreaterThan(SERIES_WEEKS);
			}
		}
	});

	it('shows a sermon as a series week only when it has questions to discuss', () => {
		const s = { slug: 's', title: 'T', scripture_ref: 'John 3:16', word_count: 4000, author_name: 'A', author_slug: 'a' };
		expect(toForSermon({ ...s, study_questions: [] })).toBeNull();
		expect(toForSermon(s)).toBeNull();
		expect(toForSermon({ ...s, study_questions: [{ question: 'Q', answer: 'A' }] })).toEqual({
			slug: 's',
			title: 'T',
			scripture_ref: 'John 3:16',
			author: { slug: 'a', name: 'A' },
			questions: 1,
			word_count: 4000
		});
	});

	it('names works whose three editions are all published, with backups', () => {
		for (const p of FOR_PAGES) {
			if (!p.levels) continue;
			const whole = p.levels.filter((b) => ['-children', '-teens', ''].every((x) => publishedInFixture(b + x)));
			expect(whole, p.slug).toEqual(p.levels);
			expect(p.levels.length, p.slug).toBeGreaterThan(LEVELS_SHOWN);
		}
	});

	it('lays out a work youngest first, skipping one missing an edition', () => {
		const english = ['a', 'a-teens', 'a-children', 'b', 'b-children', 'c-children', 'c-teens', 'c'].map(
			(slug) => ({ slug, title: slug, author: { slug: 'x', name: 'X' } }) as unknown as BookSummary
		);
		const levels = forLevels(english, ['b', 'a', 'c']);
		expect(levels[0].map((r) => r.rung)).toEqual(['children', 'teens', 'full']);
		expect(levels.map((f) => f.map((r) => r.book.slug))).toEqual([
			['a-children', 'a-teens', 'a'],
			['c-children', 'c-teens', 'c']
		]);
	});

	it("draws a language's row from its own lists: its picks first, then its other works", () => {
		const books = ['z', 'p2', 'y-children', 'p1', 'x', 'w', 'p1-teens'].map(
			(slug) => ({ slug, title: slug, author: { slug: 'x', name: 'X' } }) as unknown as BookSummary
		);
		const row = forLanguage('sw', { books, sermons: 3, plans: 0 }, ['p1', 'p1-teens', 'missing', 'p2', 'p1']);
		expect(row).toMatchObject({ code: 'sw', name: 'Swahili', native: 'Kiswahili' });
		expect(countsLine(row.counts)).toBe('5 books · 3 sermons');
		expect(countsLine({ books: 1, sermons: 1, plans: 2 })).toBe('1 book · 1 sermon · 2 reading plans');
		expect(row.counts).toEqual({ books: 5, sermons: 3, plans: 0 });
		expect(row.covers.map((b) => b.slug)).toEqual(['p1', 'p2', 'z', 'x']);
		expect(row.covers.length).toBe(LANGUAGE_COVERS);
		expect(forLanguage('lg', { books: [], sermons: 0, plans: 0 }, []).name).toBe('Luganda');
	});
});
