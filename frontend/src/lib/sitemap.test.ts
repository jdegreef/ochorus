/**
 * The split sitemap's invariants.
 *
 * Not "does it emit XML" — the things that would break QUIETLY. A per-locale
 * child that dropped its `hreflang` alternates, a section that claimed URLs in
 * the wrong locale, or an unknown section resolving to something instead of
 * nothing all still produce a valid-looking sitemap, and Search Console would
 * be weeks reporting the damage.
 */
import { describe, expect, it } from 'vitest';
import { ADVERTISED_LOCALES } from './advertised-locales';
import {
	loc,
	sectionEntries,
	sectionLocale,
	sections,
	urlXml,
	urlsetXml
} from './sitemap';
import type { Entry, SitemapData } from './sitemap';

const entry = (byLocale: Record<string, string>, lastmod?: string): Entry => ({
	byLocale: new Map(Object.entries(byLocale)),
	lastmod
});

const chapter = entry({ en: '/books/humility/1/', sw: '/books/humility/1/' });

const data = (over: Partial<SitemapData> = {}): SitemapData => ({
	pages: [],
	authors: [],
	books: [],
	sermons: [],
	scripture: [],
	chapters: [],
	...over
});

describe('a per-locale child sitemap', () => {
	it('claims only that locale’s URLs', () => {
		const xml = urlXml(chapter, 'sw');
		expect(xml).toContain(`<loc>${loc('sw', '/books/humility/1/')}</loc>`);
		expect(xml).not.toContain(`<loc>${loc('en', '/books/humility/1/')}</loc>`);
	});

	it('still lists EVERY alternate on the URL it does claim', () => {
		// The split narrows which URLs a file claims, never the hreflang set each
		// one carries. Trimming the alternates to the file's own locale would
		// dismantle the multilingual signalling the split was supposed to leave
		// untouched — and the sitemap would still look perfectly well-formed.
		const xml = urlXml(chapter, 'sw');
		expect(xml).toContain(`hreflang="en" href="${loc('en', '/books/humility/1/')}"`);
		expect(xml).toContain(`hreflang="sw" href="${loc('sw', '/books/humility/1/')}"`);
		expect(xml).toContain(`hreflang="x-default" href="${loc('en', '/books/humility/1/')}"`);
	});

	it('emits nothing for an entry that has no row in that locale', () => {
		expect(urlXml(entry({ en: '/books/only-english/1/' }), 'sw')).toBe('');
	});

	it('leaves no blank line where a skipped entry would have been', () => {
		const xml = urlsetXml(
			[entry({ en: '/a/' }), entry({ sw: '/b/' }), entry({ en: '/c/' })],
			'en'
		);
		expect(xml).not.toMatch(/\n\n/);
		expect([...xml.matchAll(/<loc>/g)]).toHaveLength(2);
	});
});

describe('urlXml without a locale filter', () => {
	it('emits one row per locale, as the flat sitemap did', () => {
		expect([...urlXml(chapter).matchAll(/<loc>/g)]).toHaveLength(2);
	});

	it('carries lastmod as a bare date when there is one, and omits it otherwise', () => {
		expect(
			urlXml(entry({ en: '/books/x/' }, '2026-08-25T19:55:13Z'))
		).toContain('<lastmod>2026-08-25</lastmod>');
		expect(urlXml(entry({ en: '/books/x/' }))).not.toContain('<lastmod>');
	});
});

describe('sections', () => {
	it('gives every advertised locale its own chapter section', () => {
		for (const l of ADVERTISED_LOCALES)
			expect(sections()).toContain(`chapters-${l}`);
	});

	it('resolves a chapter section to that locale, and a type section to none', () => {
		expect(sectionLocale('chapters-sw')).toBe('sw');
		expect(sectionLocale('books')).toBeUndefined();
	});

	it('selects only the chapters a locale actually has', () => {
		const d = data({ chapters: [chapter, entry({ en: '/books/solo/1/' })] });
		expect(sectionEntries(d, 'chapters-sw')).toHaveLength(1);
		expect(sectionEntries(d, 'chapters-en')).toHaveLength(2);
	});

	it('refuses an unknown section rather than serving an empty one', () => {
		// The route 404s on null. An empty `<urlset>` would be a 200 that
		// Search Console could accept and index as a valid, contentless sitemap.
		expect(sectionEntries(data(), 'chapters-zz')).toBeNull();
		expect(sectionEntries(data(), 'nonsense')).toBeNull();
	});

	it('gives the scripture graph its own section, carrying only English', () => {
		// These pages exist in English alone (citations parse against English book
		// names), so a second locale here would be a false alternate.
		const d = data({ scripture: [entry({ en: '/scripture/romans/8/' })] });
		expect(sectionEntries(d, 'scripture')).toHaveLength(1);
		expect(sections()).toContain('scripture');
		expect(urlXml(d.scripture[0])).not.toContain('hreflang="sw"');
	});

	it('routes topics and plans into pages, so no section goes unserved', () => {
		// Every entry `build()` produces has to reach exactly one section; a type
		// that reached none would vanish from the sitemap without any error.
		const d = data({ pages: [entry({ en: '/topics/prayer/' })] });
		expect(sectionEntries(d, 'pages')).toHaveLength(1);
	});
});
