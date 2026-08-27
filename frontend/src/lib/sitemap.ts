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
	listAuthors,
	listBooks,
	listPlans,
	listScripturePages,
	listSermons,
	listTopics
} from '$lib/library-public';
import { locales } from '$lib/paraglide/runtime';
import { ADVERTISED_LOCALES, UNADVERTISED_LOCALES } from '$lib/advertised-locales';
import { ERAS, eraOf } from '$lib/eras';

/** Locale-prefixed absolute URL ('' prefix for the default locale, en). */
export const loc = (locale: string, path: string) =>
	`${SITE_URL}${locale === 'en' ? '' : `/${locale}`}${path}`;

export interface Entry {
	/** Locale → path, for every locale where this page really exists. */
	byLocale: Map<string, string>;
	lastmod?: string;
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
	return [...entry.byLocale.entries()]
		.filter(([l]) => only === undefined || l === only)
		.map(
			([l, p]) =>
				`  <url>\n    <loc>${loc(l, p)}</loc>\n${lastmod}${alts}\n${xDefault}\n  </url>`
		)
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
		' xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' +
		body +
		'\n</urlset>\n'
	);
}

export interface SitemapData {
	/** Static app pages, era landings, topics and plans — the small tail. */
	pages: Entry[];
	/** The scripture graph. English only, so these entries carry one locale. */
	scripture: Entry[];
	authors: Entry[];
	books: Entry[];
	sermons: Entry[];
	/** Every chapter, all locales. The child routes slice this per locale. */
	chapters: Entry[];
}

/**
 * The sections the index links and the child route serves, in index order.
 *
 * Chapters are split PER LOCALE and everything else is not, because locale is
 * the axis the coverage question actually lives on ("is Swahili indexing?")
 * and chapters are the only type big enough for the split to buy anything:
 * en is 1,264 URLs, while books/sermons/authors/pages are 130/98/175/160 and
 * would gain nothing but files.
 */
export const sections = (): string[] => [
	...ADVERTISED_LOCALES.map((l) => `chapters-${l}`),
	'books',
	'sermons',
	'authors',
	'scripture',
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
			plans: await listPlans(l).catch(() => [])
		}))
	);
	const authors = await listAuthors().catch(() => []);
	// The SAME list the /scripture route entry generators build from. Reading it
	// here rather than re-deriving the floor is what keeps "advertised" and
	// "built" from drifting apart — the failure prerenderCoverage.test.ts exists
	// to catch, and which is only cheap to avoid up front.
	const scripturePages = await listScripturePages().catch(() => []);

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

	// Author pages prerender for every locale (the bio falls back to English).
	const authorSlugs = new Set<string>(authors.map((a) => a.slug));
	for (const { books } of perLocale) for (const b of books) authorSlugs.add(b.author.slug);
	const authorEntries: Entry[] = [...authorSlugs].map((slug) => ({
		byLocale: new Map(ADVERTISED_LOCALES.map((l) => [l, `/authors/${slug}/`]))
	}));

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
	const collect = (
		kind: 'books' | 'sermons' | 'topics' | 'plans',
		pathOf: (slug: string) => string,
		lastmodOf?: (item: { slug: string; updated_at?: string }) => string | undefined
	) => {
		const byWork = new Map<string, Entry>();
		for (const slice of advertisedSlices) {
			for (const item of slice[kind] as { slug: string; updated_at?: string }[]) {
				let e = byWork.get(item.slug);
				if (!e) byWork.set(item.slug, (e = { byLocale: new Map() }));
				e.byLocale.set(slice.locale, pathOf(item.slug));
				const lm = lastmodOf?.(item);
				if (lm && (!e.lastmod || lm > e.lastmod)) e.lastmod = lm;
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
	const books = collect('books', (s) => `/books/${s}/`, (b) => b.updated_at);
	const sermons = collect('sermons', (s) => `/sermons/${s}/`, (s) => s.updated_at);
	pages.push(...collect('topics', (s) => `/topics/${s}/`));
	pages.push(...collect('plans', (s) => `/plans/${s}/`));

	// Scripture pages carry ONE locale, not the advertised set: citations parse
	// only against English book names, so there is no localized version of these
	// and claiming one would be a false alternate.
	const scripture: Entry[] = [
		{ byLocale: new Map([['en', '/scripture/']]) },
		...scripturePages.map((p) => ({
			byLocale: new Map([
				[
					'en',
					`/scripture/${p.book}/${p.chapter}/` + (p.verse === null ? '' : `${p.verse}/`)
				] as [string, string]
			])
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
