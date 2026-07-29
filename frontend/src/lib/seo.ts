import { SITE_URL } from './config';
import { localizeHref, withTrailingSlash } from '$lib/href';
import { locales } from '$lib/paraglide/runtime';
import { ADVERTISED_LOCALES } from '$lib/advertised-locales';

export interface Hreflang {
	/** One alternate per locale the work actually exists in. */
	alternates: { loc: string; href: string }[];
	/** The x-default target: English when present, else the first available. */
	xDefault: string;
}

/**
 * hreflang alternates for a per-language work — a book, chapter, sermon, or
 * plan. These have NO English fallback: a locale with no row simply doesn't
 * show the item, so advertising `<link rel="alternate" hreflang>` for every
 * locale points crawlers at localized URLs that soft-404 (an English page
 * claiming Swahili/Luganda siblings that 404). We advertise an alternate only
 * for the locales the API reports the work is published in (`available`, from
 * the serializer's `available_languages`).
 *
 * When `available` is empty — an older API, or a prerender that raced the field
 * being served — we fall back to advertising every locale (the prior, lenient
 * behaviour) rather than emitting a lone self-link. Ordering follows the
 * canonical `locales` order, not the API's. x-default is English when the work
 * exists in it, else the first available locale (mirrors sitemap.xml).
 *
 * (Authors and topics do NOT use this: they render in every locale via a
 * bio/name fallback, so their all-locale hreflang is correct.)
 */
export function hreflangFor(path: string, available: string[]): Hreflang {
	const has = new Set(available);
	// Intersected with ADVERTISED_LOCALES on both paths: a locale that is wired
	// in the UI but has nothing to read must never be offered as an alternate,
	// and the empty-`available` fallback below used to advertise EVERY locale —
	// exactly the case where we know least about what exists.
	const langs = ADVERTISED_LOCALES.filter((l) => has.has(l));
	const emit = langs.length ? langs : [...ADVERTISED_LOCALES];
	const alternates = emit.map((loc) => ({
		loc,
		href: `${SITE_URL}${localizeHref(path, { locale: loc })}`
	}));
	const def = emit.includes('en') ? 'en' : emit[0];
	return { alternates, xDefault: `${SITE_URL}${localizeHref(path, { locale: def })}` };
}

/**
 * hreflang alternates for a page that exists in every ADVERTISED locale — an
 * author or a topic, which render via a bio/name fallback rather than needing
 * their own translation.
 *
 * "Every locale" is the wrong bar: a fallback page in a locale with no content
 * is English prose at a localized URL, and claiming it as that language's
 * version is a false alternate. Portuguese produced 230 of those before this
 * gate — one on every page of the site.
 */
export function hreflangAll(path: string): Hreflang {
	return hreflangFor(path, [...ADVERTISED_LOCALES]);
}

/** Make a path absolute against the site origin (pass-through for full URLs). */
export function absUrl(path: string): string {
	if (!path) return SITE_URL;
	if (/^https?:\/\//.test(path)) return path;
	// Normalize here rather than at each call site: breadcrumb items are built
	// from raw paths (`/books/${slug}`) that never pass through localizeHref, so
	// the BreadcrumbList was advertising the non-slash form — the empty shell —
	// as the canonical position of every detail page. Asset paths carry a file
	// extension and are left untouched (see withTrailingSlash).
	return SITE_URL + withTrailingSlash(path.startsWith('/') ? path : `/${path}`);
}

/**
 * A ready-to-inject <script type="application/ld+json"> string for use inside
 * <svelte:head> via {@html …}. `<` is escaped so book/author text can never
 * break out of the script tag.
 */
export function jsonLd(data: unknown): string {
	const json = JSON.stringify(data).replace(/</g, '\\u003c');
	return `<script type="application/ld+json">${json}</script>`;
}

/**
 * A schema.org ItemList as a ready-to-inject JSON-LD script — the structured
 * counterpart of a browse/shelf page, so search engines see an ordered roster
 * of the works instead of an opaque grid. `items` are {name, url} in display
 * order; urls are made absolute. Mirrors the biographies page's people list.
 */
export function itemList(name: string, items: { name: string; url: string }[]): string {
	return jsonLd({
		'@context': 'https://schema.org',
		'@type': 'ItemList',
		name,
		numberOfItems: items.length,
		itemListElement: items.map((it, i) => ({
			'@type': 'ListItem',
			position: i + 1,
			name: it.name,
			url: absUrl(it.url)
		}))
	});
}

/** schema.org BreadcrumbList from [name, url] pairs (urls made absolute). */
export function breadcrumb(items: { name: string; url: string }[]) {
	return {
		'@context': 'https://schema.org',
		'@type': 'BreadcrumbList',
		itemListElement: items.map((it, i) => ({
			'@type': 'ListItem',
			position: i + 1,
			name: it.name,
			item: absUrl(it.url)
		}))
	};
}
