import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { FOR_LINKS, forPath, forPhrase } from './forLinks';
import {
	FOR_ANCHORS,
	FOR_PAGES,
	PLANS_SHOWN,
	SHELF_SIZE,
	forPage,
	forPlans,
	forShelf,
	toOfflineBook
} from './forPages';
import type { BookDetail, BookSummary, PlanSummary } from './library-public';

const ROUTES = join(import.meta.dirname, '..', 'routes');
const LIBRARY = join(import.meta.dirname, '..', '..', '..', 'backend', 'library');
const BOOKS = join(LIBRARY, 'fixtures', 'content', 'books');
/** The plan seed, read as text: each plan slug appears quoted. */
const PLAN_SEED = readFileSync(join(LIBRARY, 'plan_seed.py'), 'utf8');

/** This slug's English book row in the content fixture, or null. */
const fixtureBook = (slug: string): { is_published: boolean; pdf_url: string } | null => {
	try {
		return JSON.parse(readFileSync(join(BOOKS, `${slug}.en.json`), 'utf8'))[0].fields;
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

	it('words a label for mid-sentence without lower-casing the Bible', () => {
		expect(forPhrase('Youth ministries')).toBe('youth ministries');
		expect(forPhrase('Bible colleges')).toBe('Bible colleges');
	});

	it('links only to routes that exist, or to a section the page has', () => {
		for (const p of FOR_PAGES) {
			const has: Record<(typeof FOR_ANCHORS)[number], boolean> = {
				'#plans': p.plans.length > 0,
				'#shelves': p.shelves.length > 0,
				'#guides': !!p.guides,
				'#offline': !!p.offline
			};
			const hrefs = [p.primary.href, p.secondary.href, ...p.points.flatMap((x) => x.link?.href ?? [])];
			for (const href of hrefs) {
				if (href.startsWith('#')) {
					expect(FOR_ANCHORS, `${p.slug}: ${href}`).toContain(href);
					expect(has[href as keyof typeof has], `${p.slug} links ${href} but has no such section`).toBe(true);
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
		for (const p of FOR_PAGES) {
			expect(p.plans.filter((s) => !PLAN_SEED.includes(`"${s}"`)), p.slug).toEqual([]);
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
});
