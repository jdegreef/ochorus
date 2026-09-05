import { SITE_URL } from './config';
import { localizeHref, withTrailingSlash } from '$lib/href';
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
 * A meta-description-sized slice of prose.
 *
 * Search engines and social scrapers truncate `<meta name="description">` and
 * `og:description` around 155–160 characters, so shipping 250–300 (the book and
 * chapter pages did) only fed the SERP a mid-word cut. This ends at a sentence
 * boundary when one falls in the back half of the budget — the cleanest read —
 * and otherwise at the last whole word with an ellipsis. Whitespace is
 * collapsed, and text already within budget is returned untouched, so it is
 * safe to wrap a short fallback string in it too.
 */
export function truncateMeta(text: string, max = 160): string {
	const clean = (text ?? '').replace(/\s+/g, ' ').trim();
	if (clean.length <= max) return clean;
	const slice = clean.slice(0, max);
	const sentence = Math.max(
		slice.lastIndexOf('. '),
		slice.lastIndexOf('! '),
		slice.lastIndexOf('? ')
	);
	// Only honour a sentence end in the back half; an early one would throw away
	// most of the budget.
	if (sentence >= max * 0.6) return slice.slice(0, sentence + 1).trim();
	const word = slice.lastIndexOf(' ');
	return (word > 0 ? slice.slice(0, word) : slice).trim() + '…';
}

/**
 * The raw schema.org ItemList object for a shelf's works — the ordered roster of
 * {name, url} pairs, urls made absolute. The shared body of the standalone
 * itemList() script and the CollectionPage's `mainEntity`, so a ListItem's shape
 * is authored once. `name` is omitted when embedded (the CollectionPage names it).
 */
function itemListObject(items: { name: string; url: string }[], name?: string) {
	return {
		'@type': 'ItemList',
		...(name ? { name } : {}),
		numberOfItems: items.length,
		itemListElement: items.map((it, i) => ({
			'@type': 'ListItem',
			position: i + 1,
			name: it.name,
			url: absUrl(it.url)
		}))
	};
}

/**
 * A schema.org ItemList as a ready-to-inject JSON-LD script — the structured
 * counterpart of a browse/shelf page, so search engines see an ordered roster
 * of the works instead of an opaque grid. `items` are {name, url} in display
 * order; urls are made absolute. Mirrors the biographies page's people list.
 */
export function itemList(name: string, items: { name: string; url: string }[]): string {
	return jsonLd({ '@context': 'https://schema.org', ...itemListObject(items, name) });
}

/**
 * A schema.org CollectionPage as a ready-to-inject JSON-LD script — the shelf
 * page itself as an entity, carrying the ItemList of its works as `mainEntity`
 * rather than leaving the list to float as its own top-level graph. `url` is a
 * full URL (the page's canonical, so the two never disagree); item urls are the
 * same {name, url} display-order pairs itemList() takes, made absolute.
 */
export function collectionPage(opts: {
	name: string;
	description: string;
	url: string;
	items: { name: string; url: string }[];
}): string {
	const { name, description, url, items } = opts;
	return jsonLd({
		'@context': 'https://schema.org',
		'@type': 'CollectionPage',
		name,
		description,
		url: absUrl(url),
		isAccessibleForFree: true,
		mainEntity: itemListObject(items)
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

/**
 * A ready-to-inject JSON-LD BreadcrumbList straight from a Breadcrumb trail's
 * `items` ({name, href}) — the visible <Breadcrumb> and the head markup then
 * read from the same array. Bridges the one field-name mismatch (`href` vs the
 * schema's `url`) in a single place, so a page can never hand-retype it wrong.
 */
export function breadcrumbLd(items: { name: string; href: string }[]): string {
	return jsonLd(breadcrumb(items.map((c) => ({ name: c.name, url: c.href }))));
}
