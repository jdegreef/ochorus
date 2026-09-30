/**
 * The split sitemap's invariants.
 *
 * Not "does it emit XML" — the things that would break QUIETLY. A per-locale
 * child that dropped its `hreflang` alternates, a section that claimed URLs in
 * the wrong locale, or an unknown section resolving to something instead of
 * nothing all still produce a valid-looking sitemap, and Search Console would
 * be weeks reporting the damage.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
	loc,
	resetSitemapData,
	sectionEntries,
	sectionLocale,
	sections,
	sitemapData,
	urlXml,
	urlsetXml,
	SCRIPTURE_SITEMAP_FLOOR
} from './sitemap';
import type { Entry, SitemapData } from './sitemap';

// `build()` reads the live catalogue; drive it with an empty API surface so the
// only rows it sees are the scripture ones this suite cares about. Hoisted by
// vitest, so it governs `sitemapData()` everywhere in this file — harmless to
// the pure-function tests above, which never call it.
// Pinned, so the author test doesn't turn vacuous when the registry changes.
vi.mock('$lib/advertised-locales', () => ({
	ADVERTISED_LOCALES: ['en', 'es', 'sw'],
	UNADVERTISED_LOCALES: []
}));

vi.mock('$lib/library-public', () => {
	const empty = async () => [];
	const author = (slug: string) => ({ slug, name: slug, photo_url: '', birth_year: null });
	return {
		// One article in English and Swahili, none in Spanish.
		listArticles: async (l = 'en') =>
			l === 'en'
				? [{ slug: 'how-to-pray', updated_at: '2026-09-01T00:00:00Z', topics: [{ slug: 'prayer', title: 'Prayer' }] }]
				: l === 'sw'
					? [{ slug: 'how-to-pray', updated_at: '2026-09-15T00:00:00Z', topics: [] }]
					: [],
		// A writer on the English shelf only, and one whose sole Swahili presence
		// is a book (no bio there) — enough to tell "every locale" from "where
		// they have something".
		listAuthors: async (l = 'en') =>
			l === 'en' ? [author('andrew-murray'), author('e-m-bounds')] : [],
		listBooks: async (l = 'en') =>
			l === 'sw'
				? [
						{
							slug: 'humility',
							author: author('andrew-murray'),
							updated_at: '2026-08-25T10:00:00Z',
							topics: [{ slug: 'prayer', title: 'Maombi' }],
							series: { slug: 'rooted', title: 'Rooted', position: 1, total: 2 }
						},
						{
							slug: 'with-christ',
							author: author('andrew-murray'),
							updated_at: '2026-09-02T10:00:00Z',
							topics: [],
							series: null
						}
					]
				: [],
		// A place hub in English and Swahili, none in Spanish.
		listHubs: async (l = 'en') =>
			l === 'en' || l === 'sw'
				? [{ kind: 'place', slug: 'wales', region: null, members: ['andrew-murray'], name: 'Wales' }]
				: [],
		listPlans: async (l = 'en') =>
			l === 'sw' ? [{ slug: 'humility-in-12', covers: [{ slug: 'humility' }] }] : [],
		listQuoteAuthors: empty,
		listQuoteTopics: empty,
		listQuoteTopicPages: empty,
		listSeries: async (l = 'en') => (l === 'sw' ? [{ slug: 'rooted' }] : []),
		listSermons: empty,
		listTopics: async (l = 'en') => (l === 'sw' ? [{ slug: 'prayer' }] : []),
		listScripturePages: async () => [
			{ book: 'romans', chapter: 8, verse: null, citing_count: 40 },
			{ book: 'jude', chapter: 1, verse: null, citing_count: 3 },
			{ book: 'romans', chapter: 8, verse: 28, citing_count: 12 },
			{ book: 'genesis', chapter: 1, verse: 26, citing_count: 5 }
		]
	};
});

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
	quotes: [],
	articles: [],
	chapters: [],
	openings: [],
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

describe('images', () => {
	const withImages = (): Entry => ({
		byLocale: new Map([
			['en', '/books/x/'],
			['sw', '/books/x/']
		]),
		images: new Map([
			['en', 'https://ochorus.com/covers/x.png'],
			['sw', 'https://ochorus.com/covers/sw/x.png']
		])
	});

	it('puts each edition’s image on its own locale’s row only', () => {
		// The Swahili page is about the Swahili cover; claiming the English card
		// for it would tell an image index the wrong title belongs to the page.
		const sw = urlXml(withImages(), 'sw');
		expect(sw).toContain('<image:loc>https://ochorus.com/covers/sw/x.png</image:loc>');
		expect(sw).not.toContain('/covers/x.png');
		expect(urlXml(withImages()).match(/<image:image>/g)).toHaveLength(2);
	});

	it('emits no image element for a row that has none', () => {
		expect(urlXml(entry({ en: '/books/y/' }))).not.toContain('image:');
	});

	it('declares the image namespace the rows use', () => {
		expect(urlsetXml([withImages()])).toContain(
			'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"'
		);
	});

	it('escapes an ampersand rather than ending the document', () => {
		const e = withImages();
		e.images!.set('en', 'https://cdn.example/x.png?a=1&b=2');
		expect(urlXml(e, 'en')).toContain('?a=1&amp;b=2');
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
	it('does not advertise chapters in ANY locale', () => {
		// Chapters were pulled from the advertised set (a large "Discovered –
		// currently not indexed" pile — see sections()). The index links only the
		// per-type children below, so no `chapters-<locale>` child — for any
		// locale — is enumerated, prerendered, or submitted to Google.
		expect(sections().some((s) => s.startsWith('chapters-'))).toBe(false);
	});

	it('advertises only each edition’s opening chapter, in one chapters child', () => {
		// The one chapter per book that came back (see sections()): not the full
		// per-locale set, which stays unlisted.
		expect(sections()).toContain('chapters');
		const d = data({ chapters: [chapter, entry({ en: '/books/humility/2/' })], openings: [chapter] });
		expect(sectionEntries(d, 'chapters')).toEqual([chapter]);
		expect(sectionLocale('chapters')).toBeUndefined();
	});

	// The per-locale chapter machinery is kept INTACT so a restore is one line
	// (re-add the `chapters-${l}` spread to sections()). These two guard that it
	// still resolves — a `chapters-<locale>` section still maps to its locale and
	// still selects the chapters that locale has — so the reversal stays cheap.
	it('still resolves a chapter section to that locale, and a type section to none', () => {
		expect(sectionLocale('chapters-sw')).toBe('sw');
		expect(sectionLocale('books')).toBeUndefined();
	});

	it('still selects only the chapters a locale actually has', () => {
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

	it('gives the articles their own section, carrying only English', () => {
		// The Articles hub, each article and each topic shelf get their own child
		// (not folded into pages) so Search Console reports them on their own line.
		// English only, like the quotes and scripture shelves.
		const d = data({ articles: [entry({ en: '/articles/prayer/' })] });
		expect(sections()).toContain('articles');
		expect(sectionEntries(d, 'articles')).toHaveLength(1);
		expect(urlXml(d.articles[0])).not.toContain('hreflang="sw"');
	});
});

describe('build() scripture entries', () => {
	// The verse-level trim lives in build(), which the injected-data tests above
	// never touch — so it needs a test that actually runs build(). Re-advertising
	// the ~557 thin verse pages is exactly the kind of change that would pass
	// every other check and only surface as a fresh "Discovered – currently not
	// indexed" pile in Search Console weeks later.
	beforeEach(() => resetSitemapData());

	it('advertises the hub and chapter-level pages but not verse-level ones', async () => {
		const { scripture } = await sitemapData();
		const urls = scripture.map((e) => e.byLocale.get('en'));
		expect(urls).toContain('/scripture/');
		expect(urls).toContain('/scripture/romans/8/');
		// Verse pages stay prerendered and crawlable (their own route entry
		// generator + the chapter page's verse links) — just not advertised here.
		expect(urls).not.toContain('/scripture/romans/8/28/');
		expect(urls).not.toContain('/scripture/genesis/1/26/');
	});

	it('does not advertise a chapter page below the sitemap floor', async () => {
		const { scripture } = await sitemapData();
		const urls = scripture.map((e) => e.byLocale.get('en'));
		expect(SCRIPTURE_SITEMAP_FLOOR).toBeGreaterThan(3);
		// Three citing passages clears the API's build floor, so the page
		// exists — it is just not promised.
		expect(urls).not.toContain('/scripture/jude/1/');
	});
});

describe('build() hub entries', () => {
	beforeEach(() => resetSitemapData());

	it('lists a hub only in the locales the API has it in, dated by its writers', async () => {
		const { pages } = await sitemapData();
		const hub = pages.find((e) => e.byLocale.get('en') === '/biographies/place/wales/');
		expect([...(hub?.byLocale.keys() ?? [])]).toEqual(['en', 'sw']);
		// Murray's newest Swahili book dates the Swahili page; English has none.
		expect(hub?.lastmods?.get('sw')).toBe('2026-09-02T10:00:00Z');
		expect(hub?.lastmods?.has('en')).toBe(false);
	});
});

describe('build() author entries', () => {
	beforeEach(() => resetSitemapData());

	const find = async (slug: string) =>
		(await sitemapData()).authors.find((e) =>
			[...e.byLocale.values()].includes(`/authors/${slug}/`)
		);

	it('advertises an author only in the locales where they have a bio or a work', async () => {
		expect([...(await find('andrew-murray'))!.byLocale.keys()]).toEqual(['en', 'sw']);
		expect([...(await find('e-m-bounds'))!.byLocale.keys()]).toEqual(['en']);
	});
});

describe('build() lastmod for pages without a date of their own', () => {
	// Each borrows the newest `updated_at` among the works it lists, in its own
	// locale — a lower bound, never an invented date (see `newest`).
	beforeEach(() => resetSitemapData());

	const page = async (path: string) =>
		(await sitemapData()).pages.find((e) => [...e.byLocale.values()].includes(path));
	const author = async (slug: string) =>
		(await sitemapData()).authors.find((e) =>
			[...e.byLocale.values()].includes(`/authors/${slug}/`)
		);

	it('dates a topic, a series and a plan by the works on them', async () => {
		expect((await page('/topics/prayer/'))?.lastmods?.get('sw')).toBe('2026-08-25T10:00:00Z');
		expect((await page('/series/rooted/'))?.lastmods?.get('sw')).toBe('2026-08-25T10:00:00Z');
		expect((await page('/plans/humility-in-12/'))?.lastmods?.get('sw')).toBe(
			'2026-08-25T10:00:00Z'
		);
	});

	it('dates an author and the book index by their newest work', async () => {
		expect((await author('andrew-murray'))?.lastmods?.get('sw')).toBe('2026-09-02T10:00:00Z');
		expect((await page('/books'))?.lastmods?.get('sw')).toBe('2026-09-02T10:00:00Z');
	});

	it("never dates one language's page by another language's change", async () => {
		// Every mocked work is Swahili: the English rows changed on no known date.
		expect((await page('/books'))?.lastmods?.has('en')).toBe(false);
		expect((await author('andrew-murray'))?.lastmods?.has('en')).toBe(false);
		const xml = urlXml((await page('/books'))!);
		expect(xml).toContain(`<loc>${loc('sw', '/books')}</loc>\n    <lastmod>2026-09-02</lastmod>`);
		expect(xml).not.toContain(`<loc>${loc('en', '/books')}</loc>\n    <lastmod>`);
	});

	it('leaves undated what lists no works', async () => {
		expect((await page('/about'))?.lastmods?.size).toBe(0);
		expect((await author('e-m-bounds'))?.lastmods?.size ?? 0).toBe(0);
	});

	it('never advertises /search or any other app-only path', async () => {
		expect(await page('/search')).toBeUndefined();
		expect(await page('/settings')).toBeUndefined();
	});
});

describe('build() the library A–Z', () => {
	beforeEach(() => resetSitemapData());

	it('advertises /authors/ in every advertised locale, dated by its books', async () => {
		const az = (await sitemapData()).pages.find((e) => e.byLocale.get('en') === '/authors/');
		expect([...az!.byLocale.keys()]).toEqual(['en', 'es', 'sw']);
		expect(az!.lastmods?.get('sw')).toBe('2026-09-02T10:00:00Z');
	});
});

describe('build() translated articles', () => {
	beforeEach(() => resetSitemapData());

	const find = async (path: string) =>
		(await sitemapData()).articles.find((e) => [...e.byLocale.values()].includes(path));

	it('lists the hub only in the locales that have articles', async () => {
		const hub = await find('/articles/');
		expect([...hub!.byLocale.keys()]).toEqual(['en', 'sw']);
		expect(hub!.lastmods?.get('sw')).toBe('2026-09-15T00:00:00Z');
	});

	it('lists each article in every locale that has it, dated per edition', async () => {
		const a = await find('/articles/how-to-pray/');
		expect([...a!.byLocale.keys()]).toEqual(['en', 'sw']);
		expect(a!.lastmods?.get('en')).toBe('2026-09-01T00:00:00Z');
		expect(a!.lastmods?.get('sw')).toBe('2026-09-15T00:00:00Z');
		const xml = urlXml(a!);
		expect(xml).toContain(`<loc>${loc('sw', '/articles/how-to-pray/')}</loc>`);
		expect(xml).toContain('hreflang="sw"');
		expect(xml).not.toContain('hreflang="es"');
	});

	it('keeps topic shelves English-only', async () => {
		const shelf = await find('/articles/prayer/');
		expect([...shelf!.byLocale.keys()]).toEqual(['en']);
	});
});
