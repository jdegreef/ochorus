import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { FOR_LINKS, forPath } from './forLinks';
import { FOR_PAGES, forPage, pickBooks } from './forPages';
import type { BookSummary } from './library-public';

const ROUTES = join(import.meta.dirname, '..', 'routes');

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

	it('gives every page enough to say, without repeats', () => {
		for (const p of FOR_PAGES) {
			expect(p.points.length, p.slug).toBeGreaterThanOrEqual(3);
			expect(p.ideas.length, p.slug).toBeGreaterThanOrEqual(3);
			// Two or more, or pickQa drops the FAQPage block.
			expect(p.questions.length, p.slug).toBeGreaterThanOrEqual(2);
			expect(new Set(p.picks).size, p.slug).toBe(p.picks.length);
			expect(p.seoDescription.length, p.slug).toBeLessThanOrEqual(160);
		}
	});

	it('picks published English books in the page order, and drops the rest', () => {
		const book = (slug: string, language = 'en') =>
			({ slug, language, title: slug, author: { slug: 'a', name: 'A', birth_year: null } }) as unknown as BookSummary;
		const all = [book('b'), book('a'), book('c', 'sw')];
		expect(pickBooks(all, ['a', 'missing', 'b', 'c']).map((b) => b.slug)).toEqual(['a', 'b']);
	});
});
