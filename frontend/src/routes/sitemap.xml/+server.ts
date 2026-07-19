import { SITE_URL } from '$lib/config';
import { listAuthors, listBooks, listPlans, listSermons, listTopics } from '$lib/library';
import { locales } from '$lib/paraglide/runtime';

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
		locales.map(async (l) => ({
			locale: l,
			books: await listBooks(l).catch(() => []),
			sermons: await listSermons(l).catch(() => []),
			topics: await listTopics(l).catch(() => []),
			plans: await listPlans(l).catch(() => [])
		}))
	);
	const authors = await listAuthors().catch(() => []);

	const entries: Entry[] = [];

	// Static app pages exist in every locale (the UI chrome is fully translated).
	for (const path of [
		'/',
		'/books',
		'/sermons',
		'/topics',
		'/plans',
		'/biographies',
		'/about',
		'/contact'
	]) {
		entries.push({ byLocale: new Map(locales.map((l) => [l, path])) });
	}

	// Author pages prerender for every locale (the bio falls back to English).
	const authorSlugs = new Set<string>(authors.map((a) => a.slug));
	for (const { books } of perLocale) for (const b of books) authorSlugs.add(b.author.slug);
	for (const slug of authorSlugs) {
		entries.push({ byLocale: new Map(locales.map((l) => [l, `/authors/${slug}/`])) });
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
		for (const slice of perLocale) {
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

	const xml =
		'<?xml version="1.0" encoding="UTF-8"?>\n' +
		'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' +
		' xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' +
		entries.map(urlXml).join('\n') +
		'\n</urlset>\n';

	return new Response(xml, { headers: { 'content-type': 'application/xml' } });
}
