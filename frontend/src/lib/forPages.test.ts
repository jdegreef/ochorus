import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { FOR_LINKS, forPath } from './forLinks';
import { FOR_PAGES, SHELF_SIZE, forPage, forShelf } from './forPages';
import type { BookSummary } from './library-public';

const ROUTES = join(import.meta.dirname, '..', 'routes');
const STATIC = join(import.meta.dirname, '..', '..', 'static');
const BOOKS = join(import.meta.dirname, '..', '..', '..', 'backend', 'library', 'fixtures', 'content', 'books');

/** Is this slug a published English book in the content fixture? */
const publishedInFixture = (slug: string) => {
	try {
		const [row] = JSON.parse(readFileSync(join(BOOKS, `${slug}.en.json`), 'utf8'));
		return row.fields.is_published === true;
	} catch {
		return false;
	}
};

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

	it('links only to routes that exist', () => {
		for (const p of FOR_PAGES) {
			const hrefs = [p.primary.href, p.secondary.href, ...p.points.flatMap((x) => x.link?.href ?? [])];
			for (const href of hrefs) {
				expect(href, `${p.slug}: ${href}`).toMatch(/^\/[a-z-]+$/);
				expect(routeExists(href), `${p.slug}: ${href}`).toBe(true);
			}
		}
	});

	it('shows a hero photo that exists, at every size it offers', () => {
		for (const p of FOR_PAGES) {
			const files = [p.photo.src, ...(p.photo.srcset?.split(',').map((c) => c.trim().split(' ')[0]) ?? [])];
			for (const f of files) expect(existsSync(join(STATIC, f)), `${p.slug}: ${f}`).toBe(true);
		}
	});

	it('gives every page enough to say, without repeats', () => {
		for (const p of FOR_PAGES) {
			expect(p.points.length, p.slug).toBeGreaterThanOrEqual(3);
			expect(p.ideas.length, p.slug).toBeGreaterThanOrEqual(3);
			// Two or more, or pickQa drops the FAQPage block.
			expect(p.questions.length, p.slug).toBeGreaterThanOrEqual(2);
			expect(new Set(p.picks).size, p.slug).toBe(p.picks.length);
			// Backups beyond the shelf, so one unpublished pick leaves no gap.
			expect(p.picks.length, p.slug).toBeGreaterThan(SHELF_SIZE);
			expect(p.seoDescription.length, p.slug).toBeLessThanOrEqual(160);
		}
	});

	it('picks books that exist, so a renamed or unpublished pick is caught here', () => {
		// The fixture is not prod's word on what is published (is_published is
		// create-only in the seed), but it is CI's — and a slug missing from it
		// is a typo or a rename.
		for (const p of FOR_PAGES) {
			const missing = p.picks.filter((s) => !publishedInFixture(s));
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
});
