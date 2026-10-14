/**
 * An "Ochorus for …" page's live sections — its starter shelves, its plans,
 * the printable leader's guides, its offline pack, its writers, its quotation,
 * the library's numbers, its sermon series, its "three levels" and its
 * languages — gathered once at build time into the snapshot the page reads
 * (routes/for-shelves). Each language's page is built from that language's
 * own lists (no English fallback), so a French page shows only French works.
 */
import { building } from '$app/environment';
import { error } from '@sveltejs/kit';
import type { ForLocale } from './forLinks';
import {
	SERIES_WEEKS,
	countWorks,
	forAuthors,
	forLanguage,
	forLevels,
	forPlans,
	forQuote,
	forShelf,
	quoteAuthor,
	toForSermon,
	toOfflineBook,
	type ForPage,
	type ForSermon,
	type ForShelfData
} from './forPages';
import {
	getAudienceShelf,
	getBook,
	getQuotePage,
	getSermon,
	guideBooks,
	listAuthors,
	listBooks,
	listPlans,
	listSermons,
	toCoverBook
} from './library-public';
import { lang } from './lang.svelte';
import { LIVE_LOCALES } from './live-locales.generated';

type Fetch = typeof globalThis.fetch;

/**
 * The library-wide lists the numbers strip and the writer cards read, fetched
 * once per build rather than once per group, and optional like the quotation:
 * a list that fails costs its section, not the build. (A failed fetch isn't
 * kept, so the next group retries.)
 */
const once = new Map<string, Promise<unknown>>();
function shared<T>(key: string, load: () => Promise<T>): Promise<T | null> {
	// Only while building: the dev server serves this live, and a list kept
	// for its lifetime would freeze the numbers at the first visit.
	if (!building) return load().catch(() => null);
	let p = once.get(key) as Promise<T | null> | undefined;
	if (!p) {
		p = load().catch(() => {
			once.delete(key);
			return null;
		});
		once.set(key, p);
	}
	return p;
}

/** The books with a printable leader's guide, children's hub first — the
 *  same two hubs, in the same order, as the guide route's prerender entries. */
async function leaderGuides(locale: ForLocale, fetch: Fetch) {
	const hubs = await Promise.all([
		getAudienceShelf('young_readers', locale, fetch),
		getAudienceShelf('teens', locale, fetch)
	]);
	return guideBooks(hubs).map(toCoverBook);
}

/** The pack's picks that are published and have a file to download, in order.
 *  Only published slugs are asked for, so an unpublished pick costs no 404. */
async function offlinePack(page: ForPage, published: Set<string>, locale: ForLocale, fetch: Fetch) {
	const slugs = (page.offline?.picks ?? []).filter((s) => published.has(s));
	const details = await Promise.all(slugs.map((s) => getBook(s, locale, fetch)));
	return details.flatMap((d) => toOfflineBook(d) ?? []);
}

/** A sermon series' weeks: its picks with study questions, in order, the
 *  first `SERIES_WEEKS`. Each pick is fetched (the list carries no questions),
 *  and one that fails, has none, or answers in another language (the sermon
 *  detail falls back to English) drops, leaving a backup in its place. */
async function sermonSeries(picks: string[], locale: ForLocale, fetch: Fetch) {
	// Through the build-wide memo: a series two pages share is fetched once.
	const weeks = await Promise.all(
		picks.map((s) =>
			shared(`sermon:${locale}:${s}`, () => getSermon(s, locale, fetch)).then(
				(d) => d && d.language === locale && toForSermon(d)
			)
		)
	);
	return weeks.filter((w): w is ForSermon => !!w).slice(0, SERIES_WEEKS);
}

/** Every live language besides the page's own the UI can link into, each
 *  from its own lists — optional like the numbers: a language whose book list
 *  fails, or holds no works, has no row, and one whose sermons or plans fail
 *  shows none. */
async function languageRows(page: ForPage, locale: ForLocale, fetch: Fetch) {
	const picks = page.shelves.flatMap((s) => s.picks);
	const rows = await Promise.all(
		LIVE_LOCALES.filter((l) => l !== locale && lang.isAvailable(l)).map(async (code) => {
			const [books, sermons, plans] = await Promise.all([
				shared(`books:${code}`, () => listBooks(code, fetch)),
				shared(`sermons:${code}`, () => listSermons(code, fetch)),
				shared(`plans:${code}`, () => listPlans(code, fetch))
			]);
			if (!books) return null;
			const row = forLanguage(code, { books, sermons: sermons?.length ?? 0, plans: plans?.length ?? 0 }, picks, locale);
			return row.counts.books ? row : null;
		})
	);
	return rows.filter((r) => r !== null);
}

/** One page's snapshot in its language. */
export async function buildForShelf(page: ForPage, locale: ForLocale, fetch: Fetch): Promise<ForShelfData> {
	// All at once: only the offline pack waits, and only on the book list.
	const books = listBooks(locale, fetch);
	const [own, allPlans, sermons, authors, guides, offline, quote, series, languages] = await Promise.all([
		books,
		listPlans(locale, fetch),
		shared(`sermons:${locale}`, () => listSermons(locale, fetch)),
		shared(`authors:${locale}`, () => listAuthors(locale, fetch)),
		page.guides ? leaderGuides(locale, fetch) : [],
		page.offline ? books.then((all) => offlinePack(page, new Set(all.map((b) => b.slug)), locale, fetch)) : [],
		// The quotation is a garnish: a quote page that fails to load costs the
		// band, not the build.
		page.quote
			? getQuotePage(quoteAuthor(page.quote), fetch).then(
					(qp) => forQuote(qp, page.quote as string),
					() => null
				)
			: null,
		Promise.all(
			(page.series ?? []).map(async (s) => ({
				title: s.title,
				note: s.note,
				sermons: await sermonSeries(s.picks, locale, fetch)
			}))
		),
		page.languages ? languageRows(page, locale, fetch) : []
	]);
	const data: ForShelfData = {
		shelves: page.shelves.map((s) => ({ title: s.title, note: s.note, books: forShelf(own, s.picks) })),
		plans: forPlans(allPlans, page.plans),
		guides,
		offline,
		authors: authors ? forAuthors(authors, page.authors) : [],
		quote,
		counts: { books: countWorks(own), sermons: sermons?.length ?? 0, plans: allPlans.length },
		series: series.filter((s) => s.sermons.length),
		levels: forLevels(own, page.levels ?? []),
		languages
	};
	// A shelf with none of its picks published: fail the build rather than ship
	// a bare heading (the picks need replacing in $lib/forPages). An empty plan,
	// guide or offline section is not an error — the page drops it, and a
	// button that pointed there goes to its fallback page instead (forHref).
	// CI's API, seeded from the fixture alone, has only a few plans.
	const empty = data.shelves.find((s) => !s.books.length);
	if (empty) error(500, `No published book on the '${locale}/${page.slug}' shelf '${empty.title}'.`);
	return data;
}
