/**
 * The sitemap, as data — shared by the index and every child sitemap.
 *
 * `sitemap.xml` used to be one flat `<urlset>` of ~2,975 URLs built inside its
 * own route. It is now a `<sitemapindex>` over per-type (and, for chapters,
 * per-locale) children, because Search Console reports indexed-vs-submitted
 * PER SITEMAP: one undifferentiated total cannot answer "are my chapter pages
 * indexing, in Swahili?", and chapters are 81% of the URLs — the whole
 * long-tail thesis. Splitting is an instrumentation change and nothing else:
 * at 2,975 URLs / 1.6 MB the file is nowhere near the protocol's 50,000-URL,
 * 50 MB ceilings and will not be this decade.
 *
 * LATER: chapters are no longer ADVERTISED at all — see `sections()` for why
 * (a large "Discovered – currently not indexed" pile) and how it stays
 * reversible. The per-locale chapter machinery below is kept intact so a
 * restore is one line; it simply isn't linked from the index today. So the
 * remaining index is per-TYPE only, and much smaller than the figures above.
 *
 * WHY THIS MODULE EXISTS. Every child route needs the same catalogue, and
 * `apiFetch` only dedupes requests that are IN FLIGHT AT ONCE (see its note).
 * Children prerender at different moments, so nine routes each calling
 * `listBooks`/`listSermons`/… would be nine independent sweeps of the API —
 * ~21 calls apiece. The cached promise below makes it one sweep for the whole
 * build, and keeps the readiness warnings firing exactly once rather than nine
 * times. Prerendering runs in a single process, so module state is a safe
 * place to hold it.
 */
import { SITE_URL } from '$lib/config';
import {
	listArticles,
	listAuthors,
	listBooks,
	listPlans,
	listQuoteAuthors,
	listQuoteTopics,
	listQuoteTopicPages,
	listScripturePages,
	listSeries,
	listSermons,
	listTopics
} from '$lib/library-public';
import { locales } from '$lib/paraglide/runtime';
import { ADVERTISED_LOCALES, UNADVERTISED_LOCALES } from '$lib/advertised-locales';
import { ERAS, eraOf } from '$lib/eras';
import { shareImage } from '$lib/coverArt';
import { absUrl } from '$lib/seo';
import { xmlEscape } from '$lib/xml';
import { ORIGINALS_PATH, ORIGINALS_SLUG } from '$lib/originals';

/** Locale-prefixed absolute URL ('' prefix for the default locale, en). */
export const loc = (locale: string, path: string) =>
	`${SITE_URL}${locale === 'en' ? '' : `/${locale}`}${path}`;

export interface Entry {
	/** Locale → path, for every locale where this page really exists. */
	byLocale: Map<string, string>;
	lastmod?: string;
	/** Locale → the absolute URL of the image that page is ABOUT: a book
	 *  edition's cover, an author's portrait. Per locale because a translated
	 *  edition's cover carries its own title. Absent where there is none. */
	images?: Map<string, string>;
}



/**
 * The `<url>` rows for one entry.
 *
 * `only` restricts the rows to a single locale — that is what makes a
 * per-locale child sitemap possible. It narrows which URLs the file CLAIMS,
 * never the `hreflang` set each one carries: a URL and its alternates do not
 * have to live in the same sitemap, but every URL must still list every
 * alternate, or the split would quietly dismantle the multilingual signalling
 * it was supposed to leave alone.
 */
export function urlXml(entry: Entry, only?: string): string {
	const alts = [...entry.byLocale.entries()]
		.map(([l, p]) => `    <xhtml:link rel="alternate" hreflang="${l}" href="${loc(l, p)}"/>`)
		.join('\n');
	// x-default follows the head-tag convention (PR #209): the English URL when
	// the work exists in English, else the first available language.
	const defLocale = entry.byLocale.has('en') ? 'en' : [...entry.byLocale.keys()][0];
	const xDefault = `    <xhtml:link rel="alternate" hreflang="x-default" href="${loc(defLocale, entry.byLocale.get(defLocale)!)}"/>`;
	const lastmod = entry.lastmod ? `    <lastmod>${entry.lastmod.slice(0, 10)}</lastmod>\n` : '';
	// One <url> per language version, each carrying the full alternate set.
	// An image rides on the row of the locale it belongs to, never on the others:
	// the Swahili page is about the Swahili cover. `image:loc` alone — Google
	// retired `image:title` and `image:caption` in 2022 and ignores them.
	return [...entry.byLocale.entries()]
		.filter(([l]) => only === undefined || l === only)
		.map(([l, p]) => {
			const img = entry.images?.get(l);
			const image = img
				? `\n    <image:image>\n      <image:loc>${xmlEscape(img)}</image:loc>\n    </image:image>`
				: '';
			return `  <url>\n    <loc>${loc(l, p)}</loc>\n${lastmod}${alts}\n${xDefault}${image}\n  </url>`;
		})
		.join('\n');
}

/** A complete `<urlset>` document for `entries`, restricted to `only` if given. */
export function urlsetXml(entries: Entry[], only?: string): string {
	const body = entries
		.map((e) => urlXml(e, only))
		.filter((s) => s !== '')
		.join('\n');
	return (
		'<?xml version="1.0" encoding="UTF-8"?>\n' +
		'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' +
		' xmlns:xhtml="http://www.w3.org/1999/xhtml"' +
		' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n' +
		body +
		'\n</urlset>\n'
	);
}

export interface SitemapData {
	/** Static app pages, era landings, topics, plans and series — the small tail. */
	pages: Entry[];
	/** The scripture graph. English only, so these entries carry one locale. */
	scripture: Entry[];
	/** Quote pages. English only, and only where a person approved them. */
	quotes: Entry[];
	/** The Articles hub, each article, and each topic-filtered shelf. English
	 *  only (original site writing, no translations yet). Its OWN child rather
	 *  than folded into `pages` so Search Console reports article indexing on its
	 *  own line — the whole reason the index is split per type. */
	articles: Entry[];
	authors: Entry[];
	books: Entry[];
	sermons: Entry[];
	/** Every chapter, all locales. The child routes slice this per locale. */
	chapters: Entry[];
}

/**
 * The sections the index links and the child route serves, in index order.
 *
 * CHAPTERS ARE DELIBERATELY NOT LISTED. They are the largest slice of the site
 * (en alone was ~1,264 URLs, ~81% of the whole index) and Search Console was
 * reporting a large "Discovered – currently not indexed" pile against them:
 * Google finding sitemap URLs it then declines to spend crawl budget fetching.
 * Pulling them from the advertised set concentrates that budget on the books,
 * authors and other landing pages the site most wants ranked. This is the same
 * move, and the same reasoning, as dropping the verse-level scripture pages
 * (see the `scripture` block in build()).
 *
 * This does NOT hide or deindex the chapters. They still prerender (the
 * `/books/[slug]/[order]` route builds every one) and stay crawlable through
 * each book page's chapter list — so Google reaches and may still index the
 * ones it judges worthwhile. We simply stop *promising* the whole set in the
 * sitemap. Fully reversible: restore the `chapters-${l}` spread below and the
 * per-locale child machinery advertises them again, because it is kept intact
 * on purpose — `sectionEntries` and `sectionLocale` still resolve a
 * `chapters-<locale>` section, and `build()` still fills `data.chapters`.
 *
 * The remaining order is DELIBERATELY not the reader-facing nav order
 * (`$lib/contentNav`). It answers a crawl/coverage question, not "what order
 * does a reader meet these in", so it does not track nav/footer/palette (F2).
 */
export const sections = (): string[] => [
	'books',
	'sermons',
	'authors',
	'scripture',
	'quotes',
	'articles',
	'pages'
];

/** The `<loc>` of a child sitemap. Root-level, deliberately — see sitemap.xml. */
export const sectionUrl = (section: string) => `${SITE_URL}/sitemap-${section}.xml`;

/** The entries a section claims, or `null` if the section name is unknown. */
export function sectionEntries(data: SitemapData, section: string): Entry[] | null {
	const chapters = section.match(/^chapters-(.+)$/);
	if (chapters) {
		const locale = chapters[1];
		if (!(ADVERTISED_LOCALES as readonly string[]).includes(locale)) return null;
		return data.chapters.filter((e) => e.byLocale.has(locale));
	}
	if (section === 'books') return data.books;
	if (section === 'sermons') return data.sermons;
	if (section === 'authors') return data.authors;
	if (section === 'scripture') return data.scripture;
	if (section === 'quotes') return data.quotes;
	if (section === 'articles') return data.articles;
	if (section === 'pages') return data.pages;
	return null;
}

/** The locale a section's rows are restricted to, if it is a per-locale one. */
export const sectionLocale = (section: string): string | undefined =>
	section.match(/^chapters-(.+)$/)?.[1];

async function build(): Promise<SitemapData> {
	// Per-locale content: a language with no row simply doesn't have the page
	// (no English fallback), so each localized URL is listed only when its
	// translation exists. Endpoint hiccups degrade to omitting that slice
	// rather than failing the whole sitemap prerender.
	const perLocale = await Promise.all(
		// Every UI locale is fetched, not just the advertised ones — the assertion
		// below needs to see a locale that has GAINED content.
		locales.map(async (l) => ({
			locale: l,
			books: await listBooks(l).catch(() => []),
			sermons: await listSermons(l).catch(() => []),
			topics: await listTopics(l).catch(() => []),
			plans: await listPlans(l).catch(() => []),
			series: await listSeries(l).catch(() => [])
		}))
	);
	const authors = await listAuthors().catch(() => []);
	// Articles: original English writing, no translations yet (like the quotes
	// hub). The same list the /articles route entry generator reads.
	const articles = await listArticles('en').catch(() => []);
	// The SAME list the /scripture route entry generators build from. Reading it
	// here rather than re-deriving the floor is what keeps "advertised" and
	// "built" from drifting apart — the failure prerenderCoverage.test.ts exists
	// to catch, and which is only cheap to avoid up front.
	const scripturePages = await listScripturePages().catch(() => []);
	// Authors whose quotations a person has REVIEWED. The same list the route's
	// entry generator builds from, so the sitemap cannot advertise a quote page
	// the review gate has not opened.
	const quoteAuthors = await listQuoteAuthors().catch(() => []);
	// The theme pages, from the same lists their route entry generators read:
	// themes deep enough to earn a page, and the (author, theme) pairs likewise.
	const quoteTopics = await listQuoteTopics().catch(() => []);
	const quoteTopicPages = await listQuoteTopicPages().catch(() => []);

	// Emission uses only the advertised locales; `perLocale` (all UI locales)
	// stays available for the drift check below.
	const worksIn = (l: string) => {
		const s = perLocale.find((x) => x.locale === l);
		return s ? s.books.length + s.sermons.length + s.topics.length + s.plans.length : 0;
	};
	// Readiness is measured in BOOKS, not in any content at all: Ochorus is a
	// library, and a locale with no books has nothing a reader came for.
	// Portuguese has exactly one sermon and no books — enough to trip a
	// "> 0 works" rule, nowhere near enough to advertise 46 pages of English
	// prose behind a Portuguese hreflang. es/sw/lg carry 10/12/18 books.
	const booksIn = (l: string) => perLocale.find((x) => x.locale === l)?.books.length ?? 0;
	// Used to THROW here: an unadvertised locale with books meant someone had
	// added content and forgotten to edit the hardcoded array. That is no longer
	// a mistake — it is the normal pre-launch state. Translating books into a
	// language while it sits in `draft` is exactly how you get it ready, and the
	// registry decides when it goes live. Failing the build on it would break the
	// very workflow the Language registry exists to support.
	//
	// So: report it, don't refuse. The nudge now points at the admin, which is
	// where the decision lives.
	const readyToPromote = UNADVERTISED_LOCALES.filter((l) => booksIn(l) > 0);
	if (readyToPromote.length) {
		console.info(
			`sitemap: ${readyToPromote.join(', ')} has books but is not live yet — ` +
				'check readiness in Admin → Languages and press Go live when ready.'
		);
	}
	// The reverse only WARNS: an advertised locale looking empty is more likely a
	// transient endpoint failure (which this file deliberately degrades on) than
	// content actually disappearing.
	for (const l of ADVERTISED_LOCALES) {
		if (l !== 'en' && worksIn(l) === 0) {
			console.warn(`sitemap: advertised locale "${l}" reported no works — API hiccup, or drop it?`);
		}
	}
	const advertisedSlices = perLocale.filter((x) =>
		(ADVERTISED_LOCALES as readonly string[]).includes(x.locale)
	);

	const pages: Entry[] = [];

	// Static app pages exist in every locale (the UI chrome is fully translated).
	for (const path of [
		'/',
		'/books',
		'/sermons',
		'/topics',
		'/plans',
		'/biographies',
		// The search page prerenders a real empty state (title, tagline, ways
		// in) precisely so it can be advertised — search/+page.ts says as much.
		// It just was never actually listed here.
		'/search',
		'/about',
		'/contact',
		'/legal'
	]) {
		pages.push({ byLocale: new Map(ADVERTISED_LOCALES.map((l) => [l, path])) });
	}

	// The quotes index is English-only, like the author quote pages it links to
	// and for the same reason: the quotations are lifted from the English works.
	// Trailing slash, because it prerenders as /quotes/index.html.
	if (quoteAuthors.length) pages.push({ byLocale: new Map([['en', '/quotes/']]) });
	// The quotes-by-topic index, English-only for the same reason. Only when a
	// theme has actually earned a page, so the hub is never advertised empty.
	if (quoteTopics.length) pages.push({ byLocale: new Map([['en', '/quotes/topics/']]) });

	// The house imprint's shelf, in each advertised locale that has one of its
	// books (no English fallback, so an empty locale has no page to list).
	const originalsIn = advertisedSlices
		.filter((x) => x.books.some((b) => b.author.slug === ORIGINALS_SLUG))
		.map((x) => [x.locale, `${ORIGINALS_PATH}/`] as [string, string]);
	if (originalsIn.length) pages.push({ byLocale: new Map(originalsIn) });

	// Articles: original English writing, no translations yet — the hub, each
	// article, and each topic-filtered shelf. Its OWN sitemap child (see
	// `articleEntries` below and the `articles` section), not folded into `pages`,
	// so Search Console reports article indexing separately. `updated_at` is a
	// trustworthy <lastmod> here (seed_articles diffs before saving, so auto_now
	// doesn't re-stamp every row on every deploy), the same reasoning as books.
	const articleEntries: Entry[] = [];
	if (articles.length) articleEntries.push({ byLocale: new Map([['en', '/articles/']]) });
	for (const a of articles) {
		articleEntries.push({
			byLocale: new Map([['en', `/articles/${a.slug}/`]]),
			lastmod: a.updated_at
		});
	}
	// A crawlable shelf per topic (`/articles/<topic>/`) — the same segment as an
	// article, prerendered by the [slug] entry generator, disambiguated in load.
	// The set is the union of the topic chips on the articles, exactly what
	// entries() emits, so advertised and built stay in step (prerenderCoverage).
	const articleTopics = new Set<string>();
	for (const a of articles) for (const tc of a.topics ?? []) articleTopics.add(tc.slug);
	for (const slug of articleTopics) {
		articleEntries.push({ byLocale: new Map([['en', `/articles/${slug}/`]]) });
	}

	// Author pages prerender for every locale (the bio falls back to English).
	const authorSlugs = new Set<string>(authors.map((a) => a.slug));
	for (const { books } of perLocale) for (const b of books) authorSlugs.add(b.author.slug);
	// The imprint is not a person and has no author page — /originals above.
	authorSlugs.delete(ORIGINALS_SLUG);
	// The portrait is the same image in every locale — an author is one row.
	const portraits = new Map(authors.filter((a) => a.photo_url).map((a) => [a.slug, a.photo_url]));
	const authorEntries: Entry[] = [...authorSlugs].map((slug) => {
		const photo = portraits.get(slug);
		const img = photo ? absUrl(photo) : null;
		return {
			byLocale: new Map(ADVERTISED_LOCALES.map((l) => [l, `/authors/${slug}/`])),
			images: img ? new Map(ADVERTISED_LOCALES.map((l) => [l, img])) : undefined
		};
	});

	// Per-era biography landing pages — only eras that actually have writers
	// (mirrors the route's entries()). Like author pages, they exist in every
	// locale (bios fall back to English).
	const presentEras = new Set(authors.map((a) => eraOf(a.birth_year)));
	for (const e of ERAS) {
		if (!presentEras.has(e.id)) continue;
		pages.push({
			byLocale: new Map(ADVERTISED_LOCALES.map((l) => [l, `/biographies/era/${e.id}/`]))
		});
	}

	// Books / sermons / topics / plans: one entry per work, listing only the
	// locales that actually have that work. Detail pages canonicalize to a
	// trailing slash (prerendered as directory indexes; the static host serves
	// those only for the trailing-slash URL).
	// Generic over the kind, so each callback is typed for the works it is
	// actually handed — a books-only `imageOf` passed for sermons is a type
	// error rather than an unchecked cast.
	type Slice = (typeof advertisedSlices)[number];
	const collect = <K extends 'books' | 'sermons' | 'topics' | 'plans' | 'series'>(
		kind: K,
		pathOf: (slug: string) => string,
		lastmodOf?: (item: Slice[K][number]) => string | undefined,
		imageOf?: (item: Slice[K][number]) => string | null
	) => {
		const byWork = new Map<string, Entry>();
		for (const slice of advertisedSlices) {
			for (const item of slice[kind] as Slice[K][number][]) {
				let e = byWork.get(item.slug);
				if (!e) byWork.set(item.slug, (e = { byLocale: new Map() }));
				e.byLocale.set(slice.locale, pathOf(item.slug));
				const lm = lastmodOf?.(item);
				if (lm && (!e.lastmod || lm > e.lastmod)) e.lastmod = lm;
				const img = imageOf?.(item);
				if (img) (e.images ??= new Map()).set(slice.locale, img);
			}
		}
		return [...byWork.values()];
	};
	// `updated_at`, not `created_at`: this field is a MODIFICATION date, and
	// feeding it a creation date told crawlers a book corrected last week was
	// last touched on its import day. Only Book and Sermon carry a trustworthy
	// one — `seed_books`/`seed_sermons` diff before saving, so `auto_now` does
	// not re-stamp every row on every deploy, which is what makes it honest
	// enough to publish. Topics, plans and chapters have no such field and get
	// NO lastmod: omitting it says "I don't know", which is true, where a
	// substitute date would be a claim. It stays optional here so an API
	// running behind this build (separate Render services, always a skew
	// window) simply omits the tag rather than breaking the sitemap.
	// The same raster the book page hands scrapers as its og:image, so a search
	// engine and a link preview see one picture of each edition.
	const books = collect(
		'books',
		(s) => `/books/${s}/`,
		(b) => b.updated_at,
		(b) => {
			const img = shareImage(b);
			return img ? absUrl(img.url) : null;
		}
	);
	const sermons = collect('sermons', (s) => `/sermons/${s}/`, (s) => s.updated_at);
	pages.push(...collect('topics', (s) => `/topics/${s}/`));
	pages.push(...collect('plans', (s) => `/plans/${s}/`));
	// A series has a page only where it has a name and a book (no English
	// fallback), which is exactly what each locale's list holds.
	pages.push(...collect('series', (s) => `/series/${s}/`));

	// Scripture pages carry ONE locale, not the advertised set: citations parse
	// only against English book names, so there is no localized version of these
	// and claiming one would be a false alternate.
	//
	// VERSE-LEVEL pages (/scripture/<book>/<ch>/<verse>/) are deliberately NOT
	// advertised here — only the hub and the chapter-level pages are. They are
	// the thinnest tier of the graph and the largest removable slice of the
	// sitemap (~557 of ~1,197 scripture URLs, ~8% of the whole index), and
	// Search Console was reporting a large "Discovered – currently not indexed"
	// pile: Google finding sitemap URLs it then declines to spend crawl budget
	// fetching. Dropping the thinnest tier from the advertised set concentrates
	// that budget on the chapters, books and chapter-level scripture pages the
	// site actually wants ranked.
	//
	// This does NOT hide or deindex the verse pages. They still prerender (their
	// own route entry generator builds them, keyed on `verse !== null`) and stay
	// crawlable through the "verses these writers stop at" links on each
	// chapter-level page — so Google reaches and may still index the ones it
	// judges worthwhile. We simply stop *promising* them in the sitemap. Fully
	// reversible: restore the `.filter` to advertise them again.
	//
	// The prerender-coverage guard enforces sitemap ⊆ prerendered, so shrinking
	// the advertised set (never growing it past what is built) keeps it green.
	const scripture: Entry[] = [
		{ byLocale: new Map([['en', '/scripture/']]) },
		...scripturePages
			.filter((p) => p.verse === null)
			.map((p) => ({
				byLocale: new Map([
					['en', `/scripture/${p.book}/${p.chapter}/`] as [string, string]
				])
			}))
	];

	// Quote pages carry ONE locale, like the scripture graph and for the same
	// reason: the quotations are lifted from the English works and every citation
	// names an English chapter.
	const quotes: Entry[] = [
		...quoteAuthors.map((a) => ({
			byLocale: new Map([['en', `/quotes/${a.slug}/`]] as [string, string][])
		})),
		// "Quotes on X" — one per theme deep enough to have earned a page.
		...quoteTopics.map((tp) => ({
			byLocale: new Map([['en', `/quotes/topics/${tp.slug}/`]] as [string, string][])
		})),
		// "<Author> Quotes on X" — one per (author, theme) pair over the threshold.
		...quoteTopicPages.map((p) => ({
			byLocale: new Map([['en', `/quotes/${p.author}/${p.topic}/`]] as [string, string][])
		}))
	];

	// Chapter pages (prerendered): one entry per (work, chapter), again listing
	// only the locales whose edition actually has that chapter.
	const byChapter = new Map<string, Entry>();
	for (const slice of advertisedSlices) {
		for (const b of slice.books) {
			for (let order = 1; order <= b.chapter_count; order++) {
				const key = `${b.slug}#${order}`;
				let e = byChapter.get(key);
				if (!e) byChapter.set(key, (e = { byLocale: new Map() }));
				e.byLocale.set(slice.locale, `/books/${b.slug}/${order}/`);
			}
		}
	}

	return {
		pages,
		authors: authorEntries,
		books,
		sermons,
		scripture,
		quotes,
		articles: articleEntries,
		chapters: [...byChapter.values()]
	};
}

let cached: Promise<SitemapData> | null = null;

/** The catalogue, fetched once per build and shared by every sitemap route. */
export const sitemapData = (): Promise<SitemapData> => (cached ??= build());

/** Testing seam: drop the cached sweep so the next call re-fetches. */
export const resetSitemapData = () => {
	cached = null;
};
