import { SITE_URL } from './config';
import { localizeHref, withTrailingSlash } from '$lib/href';
import { ADVERTISED_LOCALES } from '$lib/advertised-locales';

/**
 * The publisher's node in every page's structured data. One `@id` for the one
 * organisation, so the book, chapter, sermon and article that each name
 * Ochorus as publisher resolve to the same entity (and the home page's
 * WebSite points at it) instead of a dozen unlinked "Organization: Ochorus"
 * strings. Carried in full wherever it is used, since an `@id` only resolves
 * within a page. No `sameAs`: the organisation has no profiles elsewhere yet —
 * add them here when it does, and every page gains them.
 */
export const ORG_ID = `${SITE_URL}/#organization`;
export const WEBSITE_ID = `${SITE_URL}/#website`;

export const publisherLd = () => ({
	'@type': 'Organization',
	'@id': ORG_ID,
	name: 'Ochorus',
	url: `${SITE_URL}/`,
	logo: {
		'@type': 'ImageObject',
		url: `${SITE_URL}/icons/icon-512.png`,
		width: 512,
		height: 512
	}
});

/** The Public Domain Mark — a public-domain work's `license` in JSON-LD. The
 *  API decides which editions may claim it (`public_domain`; library/rights). */
export const PUBLIC_DOMAIN_MARK = 'https://creativecommons.org/publicdomain/mark/1.0/';

/** The `@id` of the Person (or imprint) an author page is about, from that
 *  page's absolute URL — so a book naming its author links to the same node. */
export const personId = (authorUrl: string) => `${authorUrl}#person`;

/** The `@id` of the Book an edition page is about, from its absolute URL. */
export const bookId = (bookUrl: string) => `${bookUrl}#book`;

/**
 * Open Graph locale codes (language_TERRITORY — what Facebook accepts) for the
 * UI locales. The territory is the edition's main readership, not a claim that
 * the text is regional.
 */
export const OG_LOCALES: Record<string, string> = {
	en: 'en_US',
	es: 'es_ES',
	sw: 'sw_KE',
	lg: 'lg_UG',
	pt: 'pt_PT',
	ar: 'ar_AR',
	hi: 'hi_IN',
	uk: 'uk_UA',
	fr: 'fr_FR',
	am: 'am_ET'
};

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
 * (Authors use `hreflangExact` instead; topics render in every locale via a
 * name fallback.)
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
 * hreflang alternates for exactly the advertised locales in `available` — or
 * `null` when there are none. Unlike `hreflangFor`, an empty set is an answer,
 * not "unknown": use it where `available` is authoritative and every locale
 * outside it is noindexed (an author page), so that falling back to every
 * locale would name nothing but noindexed pages.
 */
export function hreflangExact(path: string, available: string[]): Hreflang | null {
	return ADVERTISED_LOCALES.some((l) => available.includes(l)) ? hreflangFor(path, available) : null;
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
 * Plain text from an HTML fragment — every tag replaced with a space. Whitespace
 * is NOT collapsed here (a caller counting words wants the runs; one building a
 * string passes the result through truncateMeta, which collapses). Extracted
 * because the author page alone stripped bio HTML this way in three places, and
 * the same one-liner recurs across the reader/article/import surfaces.
 */
export function stripHtml(html: string): string {
	return (html ?? '').replace(/<[^>]+>/g, ' ');
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

/** Where a search result's title stops being shown (~600px of Arial). */
export const TITLE_BUDGET = 60;

const BRAND_SUFFIX = /\s+[—|-]\s+Ochorus$/;

/**
 * The `<title>` a page ships: its full title, minus the " — Ochorus" brand when
 * the title runs past the display budget.
 *
 * A long title isn't a ranking penalty (Google reads every word of it), but
 * past ~60 characters it is cut off in the result, and it is more likely to be
 * rewritten from the page's headings. The brand is the one part worth giving
 * up: Google prints the site name above every result anyway, and the words in
 * front of it (book, chapter, author, "read free online") are the ones people
 * type. So a short title keeps its brand and a long one drops it. Nothing else
 * is cut: the words that make a title match a query are worth more than fitting
 * the display.
 */
export function fitTitle(title: string, max = TITLE_BUDGET): string {
	const clean = (title ?? '').replace(/\s+/g, ' ').trim();
	return clean.length > max ? clean.replace(BRAND_SUFFIX, '') : clean;
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

/**
 * The topical shelves a work or writer belongs to, as schema.org Thing[] with
 * resolvable topic URLs. The shared shape behind a Book's `about` and a Person's
 * `knowsAbout`, so the two describe the same topic identically. Returns undefined
 * for an empty list — an omitted property rather than an empty array in the markup.
 */
export function topicThings(topics: { slug: string; title: string }[]) {
	return topics.length
		? topics.map((t) => ({
				'@type': 'Thing',
				name: t.title,
				url: absUrl(localizeHref(`/topics/${t.slug}`))
			}))
		: undefined;
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

/**
 * Locales whose supplementary UI copy — FAQ headings, reflection-question
 * headings — has been translated AND native-reviewed. Every advertised locale
 * carries the KEYS (catalogue parity is enforced), but the un-reviewed ones hold
 * the English source as a gated-off placeholder; a page renders these extras
 * only for the locales in this set, so nothing unreviewed reaches a reader. The
 * one copy: the book page (FAQ) and the sermon page (reflection questions) both
 * gate on it, so adding a reviewed locale is one edit, not two that drift. Add a
 * locale here once a native speaker has checked its keys.
 */
export const REVIEWED_UI_LOCALES = new Set(['en', 'es', 'pt', 'fr']);

/**
 * A schema.org FAQPage as a ready-to-inject JSON-LD script, built from the same
 * {q, a} pairs the page renders as its visible accordion — so the markup and the
 * on-page questions can never drift. Each entry becomes a Question with a single
 * accepted Answer, which is the shape answer engines reconcile against. (Google
 * restricted FAQ *rich-result display* to authoritative sites in 2023; the markup
 * still carries real value for answer/AI engines and as a clean entity signal.)
 * Answers are plain text — callers strip any HTML before passing them in.
 */
export function faqPage(items: { q: string; a: string }[]): string {
	return jsonLd({
		'@context': 'https://schema.org',
		'@type': 'FAQPage',
		mainEntity: items.map((it) => ({
			'@type': 'Question',
			name: it.q,
			acceptedAnswer: { '@type': 'Answer', text: it.a }
		}))
	});
}

/**
 * The two-tier Q&A contract in one place: prefer the editorial set once it clears
 * the two-item floor a real Q&A section needs, otherwise fall back to the derived
 * one, and build the FAQPage JSON-LD from whichever won. Returns the single array
 * the page renders AND the JSON-LD built from it, so the visible answers and the
 * structured data can never assert different questions. Book, author and topic
 * pages share this rather than re-hand-rolling the `>= 2` floor and the
 * `faqPage()` wiring per page (docs/questions-and-answers-plan.md §3.2–3.4).
 */
export function pickQa(
	editorial: { q: string; a: string }[],
	derived: { q: string; a: string }[]
): { items: { q: string; a: string }[]; ld: string } {
	const items = editorial.length >= 2 ? editorial : derived;
	return { items, ld: items.length ? faqPage(items) : '' };
}
