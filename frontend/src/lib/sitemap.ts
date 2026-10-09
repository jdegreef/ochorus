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
 * (Only each edition's OPENING chapter is advertised again, in one `chapters`
 * child — see `sections()`.)
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
	getAudienceShelf,
	listArticles,
	listAuthors,
	listBooks,
	listHubs,
	listPlans,
	listQuoteAuthors,
	listQuoteTopics,
	listQuoteTopicPages,
	listScripturePages,
	listSeries,
	listSermons,
	listTopics,
	MODERN_EDITION,
	type Hub
} from '$lib/library-public';
import { hubPath } from '$lib/hubs';
import { locales } from '$lib/paraglide/runtime';
import { ADVERTISED_LOCALES, UNADVERTISED_LOCALES } from '$lib/advertised-locales';
import { ERAS, eraOf } from '$lib/eras';
import { shareImage } from '$lib/coverArt';
import { absUrl } from '$lib/seo';
import { xmlEscape } from '$lib/xml';
import { ORIGINALS_PATH, ORIGINALS_SLUG } from '$lib/originals';
import { FOR_INDEX, FOR_LINKS, forPath } from '$lib/forLinks';
import { AUDIENCE_HUBS } from '$lib/audienceHub';
import { hubLanguages } from '$lib/audienceHubData';
import { APP_ONLY } from '$lib/robots';
import { withTrailingSlash } from '$lib/href';
import { modernChapterPath } from '$lib/reading-schema';

/** Locale-prefixed absolute URL ('' prefix for the default locale, en). */
export const loc = (locale: string, path: string) =>
	`${SITE_URL}${locale === 'en' ? '' : `/${locale}`}${path}`;

/**
 * The newest of `dates` (ISO strings sort chronologically), or undefined.
 *
 * The `<lastmod>` of a page that has no modification date of its own but LISTS
 * works that do — an author, a topic, a series, a plan, an index. Such a page
 * does change when one of its works does (the card's title, cover, blurb), so
 * the newest member date is a true lower bound. It understates an edit to the
 * page's own prose (a bio, a topic intro), which is the safe direction: a
 * sitemap claiming a change that did not happen is what gets lastmod ignored.
 */
export const newest = (dates: Iterable<string | undefined | null>): string | undefined => {
	let max: string | undefined;
	for (const d of dates) if (d && (!max || d > max)) max = d;
	return max;
};

/** Raise `m[k]` to `date` if it is newer. */
function bump(m: Map<string, string>, k: string, date: string | undefined | null) {
	const cur = m.get(k);
	if (date && (!cur || date > cur)) m.set(k, date);
}

/** Locale → date for `locales`, leaving out the undated. */
const dated = (locales: readonly string[], dateOf: (locale: string) => string | undefined) =>
	new Map(
		locales.flatMap((l) => {
			const d = dateOf(l);
			return d ? [[l, d] as [string, string]] : [];
		})
	);

export interface Entry {
	/** Locale → path, for every locale where this page really exists. */
	byLocale: Map<string, string>;
	/** The same date for every locale's row. */
	lastmod?: string;
	/** Locale → date, where each language's copy changes on its own (a book
	 *  edition, a localized shelf). Wins over `lastmod` for its locale. */
	lastmods?: Map<string, string>;
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
	// One <url> per language version, each carrying the full alternate set.
	// An image rides on the row of the locale it belongs to, never on the others:
	// the Swahili page is about the Swahili cover. `image:loc` alone — Google
	// retired `image:title` and `image:caption` in 2022 and ignores them.
	return [...entry.byLocale.entries()]
		.filter(([l]) => only === undefined || l === only)
		.map(([l, p]) => {
			const lm = entry.lastmods?.get(l) ?? entry.lastmod;
			const lastmod = lm ? `    <lastmod>${lm.slice(0, 10)}</lastmod>\n` : '';
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
	/** The Articles hub, each article (in every advertised locale that has it),
	 *  and each topic-filtered shelf (English only). Its OWN child rather
	 *  than folded into `pages` so Search Console reports article indexing on its
	 *  own line — the whole reason the index is split per type. */
	articles: Entry[];
	authors: Entry[];
	books: Entry[];
	sermons: Entry[];
	/** Every ENGLISH chapter. The child routes slice this per locale. */
	chapters: Entry[];
	/** Each English edition's OPENING chapter — the one chapter per book the
	 *  sitemap advertises (the `chapters` section); see `sections()`. */
	openings: Entry[];
	/** Every chapter of the Modern English edition, at its own address
	 *  (`/books/<slug>/modern/<n>/`) — the `modern` section. */
	modern: Entry[];
	/** Each printable leader's guide (`/books/<slug>/guide/`), in every
	 *  advertised locale with a guide of its own — the `guides` section. */
	guides: Entry[];
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
 * sitemap. Reversible: restore the `chapters-${l}` spread below and the
 * per-locale child machinery advertises them again — for English only, unless
 * `chapterSlices` in build() is widened too (the translated chapters are off by
 * that second switch; see there). The machinery is kept intact
 * on purpose — `sectionEntries` and `sectionLocale` still resolve a
 * `chapters-<locale>` section, and `build()` still fills `data.chapters`.
 *
 * ONE CHAPTER PER BOOK COMES BACK: the `chapters` section advertises each
 * edition's opening chapter (`openings`), and only that — ~1 URL per book per
 * advertised locale, not the ~20 of the full set. It is the one chapter a
 * searcher who wants to START a book ("<title> chapter 1", "read <title>
 * online") lands on, the highest-intent chapter URL there is, and a pile that
 * size is one Google can actually get through. It also brings those pages
 * back into IndexNow, which submits from the sitemap. Dated by the book's own
 * `updated_at`, so a corrected edition asks for a recrawl of its first page.
 * If Search Console shows these indexing well, widening the rule (chapter 2,
 * the longest chapters) is a change to `openings` alone. English editions only:
 * no translated chapter is advertised (see `chapterSlices` in build()).
 *
 * THE MODERN ENGLISH EDITION IS LISTED WHOLE (`modern`), once reviewed. The
 * reasoning above is about public-domain text that older libraries already
 * serve, which Google reads as duplicates; the modern edition is Ochorus's own
 * wording, so every chapter of it is a page only this site has.
 *
 * The remaining order is DELIBERATELY not the reader-facing nav order
 * (`$lib/contentNav`). It answers a crawl/coverage question, not "what order
 * does a reader meet these in", so it does not track nav/footer/palette (F2).
 */
export const sections = (): string[] => [
	'books',
	'chapters',
	'modern',
	'guides',
	'sermons',
	'authors',
	'scripture',
	'quotes',
	'articles',
	'pages'
];

/**
 * How many citing passages a chapter-level scripture page needs before the
 * sitemap advertises it. Deliberately ABOVE the API's build floor
 * (`scripture_graph.CHAPTER_FLOOR`, 3): that one decides whether a page is
 * worth a URL at all, this one whether it is worth a crawl we ask for.
 */
export const SCRIPTURE_SITEMAP_FLOOR = 6;

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
	if (section === 'chapters') return data.openings;
	if (section === 'modern') return data.modern;
	if (section === 'guides') return data.guides;
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
			series: await listSeries(l).catch(() => []),
			// Per-language rows, no English fallback — like books. Advertised
			// locales only: nothing else lists them.
			articles: (ADVERTISED_LOCALES as readonly string[]).includes(l)
				? await listArticles(l).catch(() => [])
				: [],
			// The tradition/place hubs this locale has (prose and enough writers).
			hubs: (ADVERTISED_LOCALES as readonly string[]).includes(l)
				? await listHubs(l).catch(() => [])
				: [],
			// The Biographies shelf for this locale (a bio or a work here). Only
			// the advertised locales read it — see the author entries below.
			authors: (ADVERTISED_LOCALES as readonly string[]).includes(l)
				? await listAuthors(l).catch(() => {
						// Degrades like the rest, but loudly: an empty list here drops
						// every bio-only writer from this locale's author entries.
						console.warn(`sitemap: author list for "${l}" failed — bio-only authors omitted`);
						return [];
					})
				: []
		}))
	);
	// English is always advertised, so its shelf is already fetched above.
	const authors = perLocale.find((x) => x.locale === 'en')?.authors ?? [];
	// English articles: the list the /articles route entry generator reads (the
	// topic shelves are built from it). The other locales' ride in `perLocale`.
	const articles = perLocale.find((x) => x.locale === 'en')?.articles ?? [];
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
	// The languages each young-reader hub has something in — the same list its
	// page's hreflang reads.
	const audienceLanguages = await hubLanguages();
	// The Modern English edition's own rows — the list its route's entry
	// generator builds from, so every advertised modern chapter is a built page.
	// Only REVIEWED editions: a modern edition is AI-rewritten text, and an
	// unreviewed one is offered to Google on the same terms as an unreviewed
	// translation — not at all. `approve_translation <slug> --language
	// en-modern` is what lists it. (Absent `source_type` reads as unreviewed.)
	const modernBooks = (await listBooks(MODERN_EDITION).catch(() => [])).filter(
		(b) => b.source_type === 'ai_reviewed'
	);
	// The leader's guides: each young-reader hub's `leader_guides`, in every
	// advertised locale the hub has something in. The English ones are exactly
	// the guide route's entries; a translated one is built because its book
	// page (on that locale's hub) links it — so every URL listed is a built page.
	const guideShelves = await Promise.all(
		ADVERTISED_LOCALES.flatMap((locale) =>
			AUDIENCE_HUBS.filter((h) => audienceLanguages[h.audience].includes(locale)).map(
				async (h) => ({
					locale,
					books: (await getAudienceShelf(h.audience, locale).catch(() => null))?.leader_guides ?? []
				})
			)
		)
	);

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

	type Slice = (typeof advertisedSlices)[number];

	const pages: Entry[] = [];

	// <lastmod> for pages with no modification date of their own: the newest
	// `updated_at` among the works each one lists (see `newest`), per locale —
	// a Swahili shelf changes when a Swahili book does, not an English one.
	// One pass over each locale's works.
	const datesOf = (x: Slice) => {
		const author = new Map<string, string>();
		const topic = new Map<string, string>();
		const series = new Map<string, string>();
		const book = new Map<string, string>();
		for (const w of [...x.books, ...x.sermons]) {
			bump(author, w.author.slug, w.updated_at);
			for (const tc of w.topics ?? []) bump(topic, tc.slug, w.updated_at);
		}
		for (const b of x.books) {
			bump(book, b.slug, b.updated_at);
			if (b.series) bump(series, b.series.slug, b.updated_at);
		}
		// A plan lists its days' books; `covers` names (up to five of) them, so
		// this can understate a change to a later book — never overstate one.
		const plan = new Map(
			x.plans.flatMap((p) => {
				const d = newest((p.covers ?? []).map((c) => book.get(c.slug)));
				return d ? [[p.slug, d] as [string, string]] : [];
			})
		);
		const books = newest(book.values());
		const sermons = newest(x.sermons.map((sr) => sr.updated_at));
		return {
			author,
			topic,
			series,
			plan,
			originals: author.get(ORIGINALS_SLUG),
			seriesIndex: newest(series.values()),
			// The static index pages, by what each lists. The home page shelves
			// books and sermons alike; about/contact/legal list no works.
			index: {
				'/': newest([books, sermons]),
				'/books': books,
				'/sermons': sermons,
				'/topics': newest(topic.values()),
				'/plans': newest(plan.values()),
				'/biographies': newest(author.values())
			} as Record<string, string | undefined>
		};
	};
	const dates = new Map<string, ReturnType<typeof datesOf>>(
		advertisedSlices.map((x) => [x.locale, datesOf(x)])
	);

	// Static app pages exist in every locale (the UI chrome is fully translated).
	for (const path of [
		'/',
		'/books',
		'/sermons',
		'/topics',
		'/plans',
		'/biographies',
		'/about',
		'/contact',
		'/legal'
		// Never an app-only path (search, account, admin): those are noindexed or
		// disallowed ($lib/robots), and advertising one is a Search Console error.
	].filter((p) => !(APP_ONLY as readonly string[]).includes(p))) {
		pages.push({
			byLocale: new Map(ADVERTISED_LOCALES.map((l) => [l, path])),
			lastmods: dated(ADVERTISED_LOCALES, (l) => dates.get(l)?.index[path])
		});
	}

	// The library A–Z ($lib/authorIndex): every writer and their books in each
	// locale. Slashed — it prerenders to authors/index.html. Dated by the books
	// and the writers it lists.
	pages.push({
		byLocale: new Map(ADVERTISED_LOCALES.map((l) => [l, '/authors/'])),
		lastmods: dated(ADVERTISED_LOCALES, (l) =>
			newest([dates.get(l)?.index['/books'], dates.get(l)?.index['/biographies']])
		)
	});

	// The quotes index is English-only, like the author quote pages it links to
	// and for the same reason: the quotations are lifted from the English works.
	// Trailing slash, because it prerenders as /quotes/index.html.
	if (quoteAuthors.length)
		pages.push({
			byLocale: new Map([['en', '/quotes/']]),
			lastmod: newest(quoteAuthors.map((a) => a.updated_at))
		});
	// The quotes-by-topic index, English-only for the same reason. Only when a
	// theme has actually earned a page, so the hub is never advertised empty.
	if (quoteTopics.length)
		pages.push({
			byLocale: new Map([['en', '/quotes/topics/']]),
			lastmod: newest(quoteTopics.map((tp) => tp.updated_at))
		});

	// The "Ochorus for …" pages ($lib/forLinks): English-only, like the quotes
	// index — their copy is English content, so each has one URL. Undated: the
	// copy lives in the frontend, and no API row says when it last changed.
	pages.push({ byLocale: new Map([['en', FOR_INDEX]]) });
	for (const l of FOR_LINKS) pages.push({ byLocale: new Map([['en', forPath(l.slug)]]) });

	// The house imprint's shelf, in each advertised locale that has one of its
	// books (no English fallback, so an empty locale has no page to list).
	const originalsIn = advertisedSlices
		.filter((x) => x.books.some((b) => b.author.slug === ORIGINALS_SLUG))
		.map((x) => [x.locale, `${ORIGINALS_PATH}/`] as [string, string]);
	if (originalsIn.length) {
		const byLocale = new Map(originalsIn);
		pages.push({
			byLocale,
			lastmods: dated([...byLocale.keys()], (l) => dates.get(l)?.originals)
		});
	}

	// The Book Series index, in each advertised locale that has a series — the
	// same set the page's own hreflang names (no English fallback).
	const seriesIn = advertisedSlices
		.filter((x) => x.series.length)
		.map((x) => [x.locale, '/series/'] as [string, string]);
	if (seriesIn.length) {
		const byLocale = new Map(seriesIn);
		pages.push({
			byLocale,
			lastmods: dated([...byLocale.keys()], (l) => dates.get(l)?.seriesIndex)
		});
	}

	// The young-reader hubs, in each advertised locale where the hub has
	// something of its own (no English fallback, so an empty one is noindexed
	// and unlisted). No <lastmod>: a hub gathers several kinds of row, and a
	// date that understates a change is worse than none.
	for (const h of AUDIENCE_HUBS) {
		const byLocale = new Map(
			advertisedSlices
				.filter((x) => audienceLanguages[h.audience].includes(x.locale))
				.map((x) => [x.locale, `${h.href}/`] as [string, string])
		);
		if (byLocale.size) pages.push({ byLocale });
	}

	// Articles — the hub, each article, and each topic-filtered shelf. Its OWN
	// sitemap child (see the `articles` section), not folded into `pages`, so
	// Search Console reports article indexing separately. `updated_at` is a
	// trustworthy <lastmod> here (seed_articles diffs before saving, so auto_now
	// doesn't re-stamp every row on every deploy), the same reasoning as books.
	//
	// The hub and each article are listed in every advertised locale that has
	// them (a locale's hub only where it has any article — an empty one is
	// noindexed), with the alternates between editions; topic shelves stay
	// English-only (their SEO copy is curated English).
	const articleEntries: Entry[] = [];
	const hubIn = advertisedSlices.filter((x) => x.articles.length);
	if (hubIn.length) {
		articleEntries.push({
			byLocale: new Map(hubIn.map((x) => [x.locale, '/articles/'])),
			lastmods: new Map(
				hubIn.flatMap((x) => {
					const d = newest(x.articles.map((a) => a.updated_at));
					return d ? [[x.locale, d] as [string, string]] : [];
				})
			)
		});
	}
	const bySlug = new Map<string, Entry>();
	for (const x of advertisedSlices) {
		for (const a of x.articles) {
			let e = bySlug.get(a.slug);
			if (!e) bySlug.set(a.slug, (e = { byLocale: new Map(), lastmods: new Map() }));
			e.byLocale.set(x.locale, `/articles/${a.slug}/`);
			if (a.updated_at) e.lastmods!.set(x.locale, a.updated_at);
			// The lead book's cover, which the article sets beside its standfirst —
			// that language's edition, the same raster its own sitemap row carries.
			const cover = a.lead_book ? shareImage(a.lead_book) : null;
			if (cover) (e.images ??= new Map()).set(x.locale, absUrl(cover.url));
		}
	}
	articleEntries.push(...bySlug.values());
	// A crawlable shelf per topic (`/articles/<topic>/`) — the same segment as an
	// article, prerendered by the [slug] entry generator, disambiguated in load.
	// The set is the union of the topic chips on the articles, exactly what
	// entries() emits, so advertised and built stay in step (prerenderCoverage).
	// Keyed by the topic, valued by its newest article (possibly undefined).
	const articleTopics = new Map<string, string | undefined>();
	for (const a of articles) {
		for (const tc of a.topics ?? []) {
			articleTopics.set(tc.slug, newest([articleTopics.get(tc.slug), a.updated_at]));
		}
	}
	for (const [slug, lastmod] of articleTopics) {
		articleEntries.push({ byLocale: new Map([['en', `/articles/${slug}/`]]), lastmod });
	}

	// Author pages prerender for every locale but are advertised only where the
	// writer has a bio, a book or a sermon in that language — `hasOwnContent`,
	// which the page uses to noindex the rest. Keep the two in step. The alternates are then only the real ones, as for books.
	const authorsIn = new Map(
		advertisedSlices.map((x) => [
			x.locale,
			new Set([
				...x.authors.map((a) => a.slug),
				...x.books.map((b) => b.author.slug),
				...x.sermons.map((s) => s.author.slug)
			])
		])
	);
	const authorSlugs = new Set([...authorsIn.values()].flatMap((slugs) => [...slugs]));
	// The imprint is not a person and has no author page — /originals above.
	authorSlugs.delete(ORIGINALS_SLUG);
	// The portrait is the same image in every locale — an author is one row.
	const portraits = new Map(authors.filter((a) => a.photo_url).map((a) => [a.slug, a.photo_url]));
	const authorEntries: Entry[] = [...authorSlugs].map((slug) => {
		const here = ADVERTISED_LOCALES.filter((l) => authorsIn.get(l)?.has(slug));
		const photo = portraits.get(slug);
		const img = photo ? absUrl(photo) : null;
		return {
			byLocale: new Map(here.map((l) => [l, `/authors/${slug}/`])),
			lastmods: dated(here, (l) => dates.get(l)?.author.get(slug)),
			images: img ? new Map(here.map((l) => [l, img])) : undefined
		};
	});

	// Per-era biography landing pages, in each locale where the era has writers
	// on that locale's shelf — the list the page itself renders. Elsewhere the
	// page is an empty "no writers" state (and says noindex), which advertising
	// every locale used to promise: an undated-writers era in eight languages.
	// Dated, like an author page, by the newest work of the writers it lists.
	for (const e of ERAS) {
		const inEra = new Map<string, string[]>(
			advertisedSlices.map((x) => [
				x.locale,
				x.authors.filter((a) => eraOf(a.birth_year) === e.id).map((a) => a.slug)
			])
		);
		const here = ADVERTISED_LOCALES.filter((l) => inEra.get(l)?.length);
		if (!here.length) continue;
		pages.push({
			byLocale: new Map(here.map((l) => [l, `/biographies/era/${e.id}/`])),
			lastmods: dated(here, (l) => newest(inEra.get(l)!.map((s) => dates.get(l)?.author.get(s))))
		});
	}

	// Tradition and place hubs — per locale, only where the API lists the hub
	// (it exists there: prose and enough listed writers), so no URL is
	// advertised that the locale's crawl never reaches. Dated like an era page,
	// by the newest work of the writers it lists in that locale.
	const hubsBySlug = new Map<string, Map<string, Hub>>();
	for (const { locale, hubs } of perLocale)
		for (const h of hubs) {
			if (!hubsBySlug.has(h.slug)) hubsBySlug.set(h.slug, new Map());
			hubsBySlug.get(h.slug)!.set(locale, h);
		}
	for (const byLang of hubsBySlug.values()) {
		const here = ADVERTISED_LOCALES.filter((l) => byLang.has(l));
		if (!here.length) continue;
		const path = `${hubPath(byLang.get(here[0])!)}/`;
		pages.push({
			byLocale: new Map(here.map((l) => [l, path])),
			lastmods: dated(here, (l) =>
				newest(byLang.get(l)!.members.map((s) => dates.get(l)?.author.get(s)))
			)
		});
	}

	// Books / sermons / topics / plans: one entry per work, listing only the
	// locales that actually have that work. Detail pages canonicalize to a
	// trailing slash (prerendered as directory indexes; the static host serves
	// those only for the trailing-slash URL).
	// Generic over the kind, so each callback is typed for the works it is
	// actually handed — a books-only `imageOf` passed for sermons is a type
	// error rather than an unchecked cast.
	const collect = <K extends 'books' | 'sermons' | 'topics' | 'plans' | 'series'>(
		kind: K,
		pathOf: (slug: string) => string,
		lastmodOf?: (item: Slice[K][number], locale: string) => string | undefined,
		imageOf?: (item: Slice[K][number]) => string | null,
		keep: (item: Slice[K][number]) => boolean = () => true
	) => {
		const byWork = new Map<string, Entry>();
		for (const slice of advertisedSlices) {
			for (const item of (slice[kind] as Slice[K][number][]).filter(keep)) {
				let e = byWork.get(item.slug);
				if (!e) byWork.set(item.slug, (e = { byLocale: new Map() }));
				e.byLocale.set(slice.locale, pathOf(item.slug));
				const lm = lastmodOf?.(item, slice.locale);
				if (lm) (e.lastmods ??= new Map()).set(slice.locale, lm);
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
	// enough to publish. Topics, plans and series have no such field and borrow
	// the newest date of the works they list (below; see `newest`) — a lower
	// bound, never an invented date. It stays optional here so an API
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
	// A sermon page shows its preacher's portrait by the byline — the one image
	// on it that is about the page (the og card is drawn text, not shown there).
	const sermons = collect(
		'sermons',
		(s) => `/sermons/${s}/`,
		(s) => s.updated_at,
		(s) => {
			const photo = s.author.photo_url || portraits.get(s.author.slug);
			return photo ? absUrl(photo) : null;
		}
	);
	// A shelf below the API's works floor in a locale is served but noindexed
	// there (`indexable`, see the topic page), so it is not promised here.
	pages.push(
		...collect(
			'topics',
			(s) => `/topics/${s}/`,
			(t, l) => dates.get(l)?.topic.get(t.slug),
			undefined,
			(t) => t.indexable !== false
		)
	);
	pages.push(...collect('plans', (s) => `/plans/${s}/`, (p, l) => dates.get(l)?.plan.get(p.slug)));
	// A series has a page only where it has a name and a book (no English
	// fallback), which is exactly what each locale's list holds.
	pages.push(
		...collect('series', (s) => `/series/${s}/`, (sr, l) => dates.get(l)?.series.get(sr.slug))
	);

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
	//
	// The same move again for the thinnest CHAPTER-level pages: one below
	// SCRIPTURE_SITEMAP_FLOOR citing passages is the ASV chapter (text found on
	// every Bible site) plus a handful of excerpts. They keep
	// their URL, their links and their indexability; they are just not promised.
	//
	// Each is dated by the newest edit among the books it quotes (the API's
	// `updated_at`), and the hub by the newest of those.
	const advertisedScripture = scripturePages.filter(
		(p) => p.verse === null && p.citing_count >= SCRIPTURE_SITEMAP_FLOOR
	);
	// Book → newest edit among its advertised chapters (`bump` keeps the max).
	const scriptureByBook = new Map<string, string>();
	for (const p of advertisedScripture) {
		if (!scriptureByBook.has(p.book)) scriptureByBook.set(p.book, '');
		bump(scriptureByBook, p.book, p.updated_at);
	}
	const scripture: Entry[] = [
		{
			byLocale: new Map([['en', '/scripture/']]),
			lastmod: newest(scripturePages.map((p) => p.updated_at))
		},
		// A book page (/scripture/<book>/) is advertised when at least one of its
		// chapters is: it aggregates them, so it is never the thinner page. Dated
		// by the newest of those chapters.
		...[...scriptureByBook].map(([book, date]) => ({
			byLocale: new Map([['en', `/scripture/${book}/`] as [string, string]]),
			lastmod: date || undefined
		})),
		...advertisedScripture.map((p) => ({
			byLocale: new Map([['en', `/scripture/${p.book}/${p.chapter}/`] as [string, string]]),
			lastmod: p.updated_at ?? undefined
		}))
	];

	// Quote pages carry ONE locale, like the scripture graph and for the same
	// reason: the quotations are lifted from the English works and every citation
	// names an English chapter. Each is dated by its newest reviewed quotation.
	const quotes: Entry[] = [
		...quoteAuthors.map((a) => ({
			byLocale: new Map([['en', `/quotes/${a.slug}/`]] as [string, string][]),
			lastmod: a.updated_at ?? undefined
		})),
		// "Quotes on X" — one per theme deep enough to have earned a page.
		...quoteTopics.map((tp) => ({
			byLocale: new Map([['en', `/quotes/topics/${tp.slug}/`]] as [string, string][]),
			lastmod: tp.updated_at ?? undefined
		})),
		// "<Author> Quotes on X" — one per (author, theme) pair over the threshold.
		...quoteTopicPages.map((p) => ({
			byLocale: new Map([['en', `/quotes/${p.author}/${p.topic}/`]] as [string, string][]),
			lastmod: p.updated_at ?? undefined
		}))
	];

	// Chapter pages are ENGLISH ONLY, here and in the openings below. Every
	// translated chapter is unreviewed AI text, and offering ~2,000 of them is
	// what Google's scaled-content policy is written against — the risk lands on
	// the whole locale, book pages included. They still prerender, link and
	// read; they are just not promised (and the chapter page carries no hreflang
	// for the same reason). Widening this again is a locale filter here.
	const chapterSlices = advertisedSlices.filter((x) => x.locale === 'en');

	// Chapter pages (prerendered): one entry per (work, chapter).
	const byChapter = new Map<string, Entry>();
	for (const slice of chapterSlices) {
		for (const b of slice.books) {
			for (let order = 1; order <= b.chapter_count; order++) {
				const key = `${b.slug}#${order}`;
				let e = byChapter.get(key);
				if (!e) byChapter.set(key, (e = { byLocale: new Map() }));
				e.byLocale.set(slice.locale, `/books/${b.slug}/${order}/`);
			}
		}
	}

	// The opening chapters — the one chapter per edition the sitemap advertises
	// (see sections()). Like a book entry: only the locales whose edition has a
	// chapter, each dated by its own edition.
	const byOpening = new Map<string, Entry>();
	for (const slice of chapterSlices) {
		for (const b of slice.books) {
			if (b.chapter_count < 1) continue;
			let e = byOpening.get(b.slug);
			if (!e) byOpening.set(b.slug, (e = { byLocale: new Map() }));
			e.byLocale.set(slice.locale, `/books/${b.slug}/1/`);
			if (b.updated_at) (e.lastmods ??= new Map()).set(slice.locale, b.updated_at);
		}
	}

	// One entry per guided work, its locales the alternates; dated per locale by
	// the edition's own row, like the book pages.
	const byGuide = new Map<string, Entry>();
	for (const { locale, books: guided } of guideShelves) {
		for (const b of guided) {
			let e = byGuide.get(b.slug);
			if (!e) byGuide.set(b.slug, (e = { byLocale: new Map() }));
			e.byLocale.set(locale, `/books/${b.slug}/guide/`);
			if (b.updated_at) (e.lastmods ??= new Map()).set(locale, b.updated_at);
		}
	}

	return {
		pages,
		guides: [...byGuide.values()],
		authors: authorEntries,
		books,
		sermons,
		scripture,
		quotes,
		articles: articleEntries,
		chapters: [...byChapter.values()],
		openings: [...byOpening.values()],
		// EVERY modern chapter, not just the opening: this is the text no other
		// library carries, so it is not the duplicate pile the original chapters
		// are. English only, like the edition. Dated by the edition's own row.
		modern: modernBooks.flatMap((b) =>
			Array.from({ length: b.chapter_count }, (_, i) => ({
				byLocale: new Map([['en', withTrailingSlash(modernChapterPath(b.slug, i + 1))] as [string, string]]),
				lastmod: b.updated_at
			}))
		)
	};
}

let cached: Promise<SitemapData> | null = null;

/** The catalogue, fetched once per build and shared by every sitemap route. */
export const sitemapData = (): Promise<SitemapData> => (cached ??= build());

/** Testing seam: drop the cached sweep so the next call re-fetches. */
export const resetSitemapData = () => {
	cached = null;
};
