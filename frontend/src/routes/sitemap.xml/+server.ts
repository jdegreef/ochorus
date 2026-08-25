import { SITE_URL } from '$lib/config';
import { listAuthors, listBooks, listPlans, listSermons, listTopics } from '$lib/library-public';
import { locales } from '$lib/paraglide/runtime';
import { ADVERTISED_LOCALES, UNADVERTISED_LOCALES } from '$lib/advertised-locales';
import { ERAS, eraOf } from '$lib/eras';

export const prerender = true;

/** Locale-prefixed absolute URL ('' prefix for the default locale, en). */
const loc = (locale: string, path: string) =>
	`${SITE_URL}${locale === 'en' ? '' : `/${locale}`}${path}`;

interface Entry {
	/** Locale → path, for every locale where this page really exists. */
	byLocale: Map<string, string>;
	lastmod?: string;
}

function urlXml(entry: Entry): string {
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
		.map(
			([l, p]) =>
				`  <url>\n    <loc>${loc(l, p)}</loc>\n${lastmod}${alts}\n${xDefault}\n  </url>`
		)
		.join('\n');
}

export async function GET() {
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

	const entries: Entry[] = [];

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
		entries.push({ byLocale: new Map(ADVERTISED_LOCALES.map((l) => [l, path])) });
	}

	// Author pages prerender for every locale (the bio falls back to English).
	const authorSlugs = new Set<string>(authors.map((a) => a.slug));
	for (const { books } of perLocale) for (const b of books) authorSlugs.add(b.author.slug);
	for (const slug of authorSlugs) {
		entries.push({ byLocale: new Map(ADVERTISED_LOCALES.map((l) => [l, `/authors/${slug}/`])) });
	}

	// Per-era biography landing pages — only eras that actually have writers
	// (mirrors the route's entries()). Like author pages, they exist in every
	// locale (bios fall back to English).
	const presentEras = new Set(authors.map((a) => eraOf(a.birth_year)));
	for (const e of ERAS) {
		if (!presentEras.has(e.id)) continue;
		entries.push({ byLocale: new Map(ADVERTISED_LOCALES.map((l) => [l, `/biographies/era/${e.id}/`])) });
	}

	// Books / sermons / topics / plans: one entry per work, listing only the
	// locales that actually have that work. Detail pages canonicalize to a
	// trailing slash (prerendered as directory indexes; the static host serves
	// those only for the trailing-slash URL).
	const collect = (
		kind: 'books' | 'sermons' | 'topics' | 'plans',
		pathOf: (slug: string) => string,
		lastmodOf?: (item: { slug: string; created_at?: string }) => string | undefined
	) => {
		const byWork = new Map<string, Entry>();
		for (const slice of advertisedSlices) {
			for (const item of slice[kind] as { slug: string; created_at?: string }[]) {
				let e = byWork.get(item.slug);
				if (!e) byWork.set(item.slug, (e = { byLocale: new Map() }));
				e.byLocale.set(slice.locale, pathOf(item.slug));
				const lm = lastmodOf?.(item);
				if (lm && (!e.lastmod || lm > e.lastmod)) e.lastmod = lm;
			}
		}
		entries.push(...byWork.values());
	};
	collect('books', (s) => `/books/${s}/`, (b) => b.created_at);
	collect('sermons', (s) => `/sermons/${s}/`);
	collect('topics', (s) => `/topics/${s}/`);
	collect('plans', (s) => `/plans/${s}/`);

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
	entries.push(...byChapter.values());

	const xml =
		'<?xml version="1.0" encoding="UTF-8"?>\n' +
		'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' +
		' xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' +
		entries.map(urlXml).join('\n') +
		'\n</urlset>\n';

	return new Response(xml, { headers: { 'content-type': 'application/xml' } });
}
