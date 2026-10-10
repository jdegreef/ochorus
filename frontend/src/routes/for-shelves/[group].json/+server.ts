/**
 * An "Ochorus for …" page's live sections — its starter shelves, its plans,
 * the printable leader's guides, its offline pack, its writers, its quotation,
 * the library's numbers, its sermon series, its "three levels" and its
 * languages — as one static JSON file
 * written at build time ($lib/forPages). The page reads this rather than the
 * live lists: the book list is ~220 books, and SvelteKit inlines a load's
 * fetched response into the prerendered HTML, so the page would carry every
 * book to draw a few rows of covers — and a client-side visit would download
 * the list again.
 */
import { building } from '$app/environment';
import { error, json } from '@sveltejs/kit';
import {
	FOR_PAGES,
	SERIES_WEEKS,
	countWorks,
	forAuthors,
	forLanguage,
	forLevels,
	forPage,
	forPlans,
	forQuote,
	forShelf,
	quoteAuthor,
	toForSermon,
	toOfflineBook,
	type ForPage,
	type ForShelfData
} from '$lib/forPages';
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
} from '$lib/library-public';
import { lang } from '$lib/lang.svelte';
import { LIVE_LOCALES } from '$lib/live-locales.generated';
import type { EntryGenerator } from './$types';

export const prerender = true;

export const entries: EntryGenerator = () => FOR_PAGES.map((p) => ({ group: p.slug }));

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
async function leaderGuides(fetch: Fetch) {
	const hubs = await Promise.all([getAudienceShelf('young_readers', 'en', fetch), getAudienceShelf('teens', 'en', fetch)]);
	return guideBooks(hubs).map(toCoverBook);
}

/** The pack's picks that are published and have a file to download, in order.
 *  Only published slugs are asked for, so an unpublished pick costs no 404. */
async function offlinePack(page: ForPage, published: Set<string>, fetch: Fetch) {
	const slugs = (page.offline?.picks ?? []).filter((s) => published.has(s));
	const details = await Promise.all(slugs.map((s) => getBook(s, 'en', fetch)));
	return details.flatMap((d) => toOfflineBook(d) ?? []);
}

/** A sermon series' weeks: its picks with study questions, in order, the
 *  first `SERIES_WEEKS`. Each pick is fetched (the list carries no questions),
 *  and one that fails or has none drops, leaving a backup in its place. */
async function sermonSeries(picks: string[], fetch: Fetch) {
	// Through the build-wide memo: a series two pages share is fetched once.
	const weeks = await Promise.all(
		picks.map((s) => shared(`sermon:${s}`, () => getSermon(s, 'en', fetch)).then((d) => d && toForSermon(d)))
	);
	return weeks.filter((w) => w !== null).slice(0, SERIES_WEEKS);
}

/** Every live language besides English the UI can link into, each from its
 *  own lists — optional like the numbers: a language whose book list fails,
 *  or holds no works, has no row, and one whose sermons or plans fail shows
 *  none. */
async function languageRows(page: ForPage, fetch: Fetch) {
	const picks = page.shelves.flatMap((s) => s.picks);
	const rows = await Promise.all(
		LIVE_LOCALES.filter((l) => l !== 'en' && lang.isAvailable(l)).map(async (code) => {
			const [books, sermons, plans] = await Promise.all([
				shared(`books:${code}`, () => listBooks(code, fetch)),
				shared(`sermons:${code}`, () => listSermons(code, fetch)),
				shared(`plans:${code}`, () => listPlans(code, fetch))
			]);
			if (!books) return null;
			const row = forLanguage(code, { books, sermons: sermons?.length ?? 0, plans: plans?.length ?? 0 }, picks);
			return row.counts.books ? row : null;
		})
	);
	return rows.filter((r) => r !== null);
}

export async function GET({ params, fetch }) {
	const page = forPage(params.group);
	if (!page) error(404, `No page for '${params.group}'.`);
	// All at once: only the offline pack waits, and only on the book list.
	const books = listBooks('en', fetch);
	const [english, allPlans, sermons, authors, guides, offline, quote, series, languages] = await Promise.all([
		books,
		listPlans('en', fetch),
		shared('sermons', () => listSermons('en', fetch)),
		shared('authors', () => listAuthors('en', fetch)),
		page.guides ? leaderGuides(fetch) : [],
		page.offline ? books.then((all) => offlinePack(page, new Set(all.map((b) => b.slug)), fetch)) : [],
		// The quotation is a garnish: a quote page that fails to load costs the
		// band, not the build.
		getQuotePage(quoteAuthor(page.quote), fetch).then(
			(qp) => forQuote(qp, page.quote),
			() => null
		),
		Promise.all(
			(page.series ?? []).map(async (s) => ({ title: s.title, note: s.note, sermons: await sermonSeries(s.picks, fetch) }))
		),
		page.languages ? languageRows(page, fetch) : []
	]);
	const data: ForShelfData = {
		shelves: page.shelves.map((s) => ({ title: s.title, note: s.note, books: forShelf(english, s.picks) })),
		plans: forPlans(allPlans, page.plans),
		guides,
		offline,
		authors: authors ? forAuthors(authors, page.authors) : [],
		quote,
		counts: { books: countWorks(english), sermons: sermons?.length ?? 0, plans: allPlans.length },
		series: series.filter((s) => s.sermons.length),
		levels: forLevels(english, page.levels ?? []),
		languages
	};
	// A shelf with none of its picks published: fail the build rather than ship
	// a bare heading (the picks need replacing in $lib/forPages). An empty plan,
	// guide or offline section is not an error — the page drops it, and a
	// button that pointed there goes to its fallback page instead (forHref).
	// CI's API, seeded from the fixture alone, has only a few plans.
	const empty = data.shelves.find((s) => !s.books.length);
	if (empty) error(500, `No published book on the '${page.slug}' shelf '${empty.title}'.`);
	return json(data);
}
