import { apiFetch, ApiError, type Fetch } from './api';
import { SITE_URL } from './config';
import { absUrl } from './seo';
import {
	ARTICLE_FIELDS,
	BOOK_FIELDS,
	CHAPTER_FIELDS,
	requireFields,
	SERMON_FIELDS
} from './payloadGuards';

export interface Author {
	slug: string;
	name: string;
	bio: string;
	photo_url: string;
	birth_year: number | null;
	death_year: number | null;
}

export type SourceType = 'public_domain' | 'ai_reviewed' | 'ai_unreviewed';

/**
 * Whether a work reached this language by translation rather than being written
 * in it. Both AI states count. The review state (`ai_unreviewed` vs
 * `ai_reviewed`) is not surfaced to readers — it drives the admin review
 * dashboard only — so this predicate now feeds just the shelf's source filter,
 * which segments a mixed shelf into "Original" and "Translated".
 */
export const isTranslated = (sourceType: SourceType): boolean =>
	sourceType !== 'public_domain';

/**
 * Content-language code of the Modern English edition (not a UI locale).
 * Defined in `reading-schema` (which imports nothing, so the storage contract
 * can hold it) and re-exported here, where the fetch helpers want it — one
 * definition, so a rename can't leave the fetched edition and the edition
 * stamped on a highlight disagreeing with no type error to show for it.
 */
export { MODERN_EDITION } from './reading-schema';

export interface BookSummary {
	slug: string;
	language: string;
	title: string;
	subtitle: string;
	/** The short title a cover sets in place of `title`; read through
	 *  `coverTitle`. Optional for the same reason as `series_position`. */
	cover_title?: string;
	author: Author;
	source_type: SourceType;
	cover_color: string;
	cover_url: string;
	/**
	 * This edition's volume in its series — the numeral its cover sets over the
	 * title. Null outside a series and in an unordered one. Optional for the
	 * same reason as `updated_at`, and for the resume cache, which holds cards
	 * stored before the field existed: absent reads as "no numeral".
	 */
	series_position?: number | null;
	chapter_count: number;
	word_count: number | null;
	/** Published topics this book belongs to (for the shelf's topic filter). */
	topics: TopicChip[];
	created_at: string;
	/**
	 * Last modification (ISO) — the sitemap's `<lastmod>`. Optional because the
	 * API and the reader deploy as separate services: an API running behind this
	 * build omits it, and the sitemap then omits the tag rather than guessing.
	 */
	updated_at?: string;
}

/**
 * What a book's cover and card draw — a `BookSummary` without the fields they
 * never read. Two places store or inline it, so its size is not free: the home
 * page's build-time snapshot (inlined into every locale's front page, see
 * `$lib/homeShelves`) and the reader's resume cache (`$lib/resumeBooks`). Every
 * other caller passes a full `BookSummary`, which fits.
 *
 * EVERY `BookSummary` field is classified, carried or dropped, and the check
 * below fails to compile on one that is neither. Both defaults were wrong: a
 * keep-list silently lost a new field from the home cards, a drop-list silently
 * inlined a new heavy one into every front page. Classifying makes it a choice.
 */
export const COVER_BOOK_KEYS = [
	'slug',
	'language',
	'title',
	'subtitle',
	'cover_title',
	'source_type',
	'cover_color',
	'cover_url',
	'series_position',
	'chapter_count',
	'word_count'
] as const;
export const COVER_BOOK_DROPS = ['topics', 'created_at', 'updated_at'] as const;
export const COVER_AUTHOR_KEYS = ['slug', 'name', 'birth_year'] as const;
export type CoverBook = Pick<BookSummary, (typeof COVER_BOOK_KEYS)[number]> & {
	author: Pick<Author, (typeof COVER_AUTHOR_KEYS)[number]>;
};
type Classified =
	| (typeof COVER_BOOK_KEYS)[number]
	| (typeof COVER_BOOK_DROPS)[number]
	| 'author';
type Unclassified = Exclude<keyof BookSummary, Classified>;
/**
 * Fails to compile, naming the field, when `BookSummary` gains an unclassified
 * one ("Type '"blurb"' does not satisfy the constraint 'never'"). Type-only:
 * nothing of it reaches the bundle.
 */
type AssertEveryFieldClassified<T extends never> = T;
export type EveryBookFieldClassified = AssertEveryFieldClassified<Unclassified>;

/** `obj` with only `keys` — the runtime half of a narrow type built from them. */
export function pick<T extends object, K extends keyof T>(obj: T, keys: readonly K[]): Pick<T, K> {
	return Object.fromEntries(keys.map((k) => [k, obj[k]])) as Pick<T, K>;
}

/** A book (or a `BookDetail`, which extends it) cut down to `CoverBook`. */
export const toCoverBook = (b: BookSummary): CoverBook => ({
	...pick(b, COVER_BOOK_KEYS),
	author: pick(b.author, COVER_AUTHOR_KEYS)
});

export interface ChapterToc {
	order: number;
	title: string;
	word_count: number;
}

export interface TopicChip {
	slug: string;
	title: string;
}

/** How a person relates to a book they are named in but did not write. */
export type PersonRole = 'featured' | 'subject' | 'mentioned';

/**
 * A person FOUND IN a book who has a bio of their own — the book detail page
 * links out to their author page. Language-gated server-side: only people with a
 * bio in this edition's language appear, so the list is never a dead link.
 */
export interface FeaturedPerson {
	slug: string;
	name: string;
	photo_url: string;
	birth_year: number | null;
	death_year: number | null;
	/** Curated relationship to the book. Carried for a UI that phrases it ("the
	 * subject of", "mentioned in"); the reader doesn't render it yet. */
	role: PersonRole;
}

/** Relative reading-difficulty badge, computed server-side; null = unjudged. */
export type Difficulty = 'accessible' | 'moderate' | 'advanced' | null;

/** A neighbouring volume of a series, as `BookSeries` links to it. */
export interface SeriesVolume {
	slug: string;
	title: string;
}

/** `BookDetail.series` — see `series_block` in the API's serializers. */
export interface BookSeries {
	slug: string;
	/** The series' name in this edition's language. */
	title: string;
	/** This volume's number; null in an unordered series (a collection). */
	position: number | null;
	/** Volume numbers the series has (ordered), or books in it here (a collection). */
	total: number;
	/** The nearest published volumes IN THIS LANGUAGE; always null in a collection. */
	previous: SeriesVolume | null;
	next: SeriesVolume | null;
}

export interface BookDetail extends BookSummary {
	description: string;
	source_url: string;
	/** A static PDF under /pdfs/ ("" = none). See library/book_export.py. */
	pdf_url: string;
	/**
	 * API path of this edition's EPUB ("" = not downloadable). Optional: an
	 * API behind this build omits it, and no button is drawn.
	 */
	epub_url?: string;
	chapters: ChapterToc[];
	topics: TopicChip[];
	related: BookSummary[];
	/**
	 * Other audience editions of the SAME work — the "(For Children)" /
	 * "(For Teens)" retellings and the full text they retell — cross-linked both
	 * ways, as cover cards (full → teens → children). Empty for the vast
	 * majority of works, which have no retelling. Derived server-side from the
	 * slug convention (`<base>` ⇄ `<base>-teens` ⇄ `<base>-children`) and gated
	 * on `is_published`, so an unpublished edition never appears here.
	 */
	editions: BookSummary[];
	/**
	 * Where this edition sits in its series — the book page's series line and
	 * the last chapter's "next in series". Null outside a series, and also when
	 * the series has no name in this edition's language (no English fallback).
	 * Optional: an API behind this build omits it, and nothing is drawn.
	 */
	series?: BookSeries | null;
	difficulty: Difficulty;
	/**
	 * The author's authoritative identifiers (Wikipedia, Wikidata), for the
	 * Person inside this page's Book markup. Only the book DETAIL payload
	 * carries them — a card emits no Person markup.
	 */
	author_same_as?: string[];
	alternate_titles?: string[];
	about_html?: string;
	/**
	 * Editorial Questions & Answers about the work — hand-authored, grounded in
	 * the book, per-language (English first). Preferred over the derived
	 * "Common questions"; the page shows a "Questions and Answers" section and
	 * emits FAQPage JSON-LD. Empty/absent = fall back to the derived set.
	 */
	qa?: { question: string; answer: string }[];
	/**
	 * The passages this book returns to most, derived from its chapters'
	 * citations — see library/scripture_graph.treated_passages. `chapters` is
	 * how many of the book's own chapters treat the passage, which is what the
	 * list is ranked by. `page` is null when the corpus-wide floor withheld a
	 * page; the server owns that floor, so only the server can say what is
	 * linkable. English editions only — the citation index is built from English
	 * bodies, so it is empty elsewhere.
	 */
	scripture?: { reference: string; chapters: number; page: ScripturePageRef | null }[];
	/**
	 * The book's first paragraph of actual prose, and the chapter it came from
	 * — see library/opening.py. Null when the front of the book yields nothing
	 * clean (an editorial synopsis, a chapter argument, an absorbed running
	 * head); the page simply shows no excerpt, which is the honest answer.
	 */
	opening?: { text: string; chapter: string } | null;
	/** Original publication year of the source work; null when unknown. */
	publication_year: number | null;
	/** This row IS the Modern English edition (language en-modern). */
	is_modern_edition: boolean;
	/** A Modern English edition of this work is published and can be read. */
	has_modern_edition: boolean;
	/** Content locales this work is actually published in (sorted, en-modern
	 * excluded) — the only locales an hreflang alternate should point at, since
	 * books are per-language rows with no English fallback. */
	available_languages: string[];
	/** Painter, title and year of the cover artwork, for the books that wear a
	 * real painting; null for every other cover. The art is Met Open Access
	 * (CC0), so this is courtesy rather than obligation — and provenance a
	 * reader can check. */
	artwork_credit: string | null;
	/**
	 * People found IN this work who have a bio of their own (not its author) —
	 * links to their author pages, in curated order. Optional so an API running
	 * behind this build simply renders no section; already language-gated, so
	 * every entry is a live link.
	 */
	featured_people?: FeaturedPerson[];
	/**
	 * How many reviewed quotations this book's author has — the page shows a
	 * "Quotes from {author}" link when it is non-zero (English only, as the quote
	 * pages are). Optional so an API running behind this build simply omits it.
	 */
	author_quote_count?: number;
	/**
	 * The reader's guide(s) for this work — the articles that explain it, linked
	 * back from a "Reader's guide" section (the reverse of an article's Read-next
	 * funnel; see library/serializers.guides_for_book). Per-language, matching
	 * `AuthorDetail.articles`: a localized edition gets its own translated guide
	 * or `[]`, never the English one. Optional so an API running behind this
	 * build omits it cleanly.
	 */
	guides?: ArticleLink[];
}

/** An article surfaced on another page that links to it — a reader's guide on
 *  the book page it explains, or an author's articles on their own page. Both
 *  sides serve the same three fields (see `guides_for_book` /
 *  `articles_for_author`) and render through `ArticleLinkCard`. */
export interface ArticleLink {
	slug: string;
	h1: string;
	description: string;
}

export interface ChapterNav {
	order: number;
	title: string;
}

export interface Chapter {
	order: number;
	title: string;
	body_html: string;
	word_count: number;
	book_title: string;
	book_slug: string;
	author_name: string;
	author_slug: string;
	/** This edition's review state, so the reader can badge an unreviewed AI
	 * translation (chapters are per-language rows under a per-language Book).
	 * Optional: a chapter page prerendered before the API served the field
	 * bakes it absent, and an absent value must read as "not translated". */
	source_type?: SourceType;
	/** This chapter belongs to the Modern English edition. */
	is_modern_edition: boolean;
	/** A Modern English edition of this work exists (offer the toggle). */
	has_modern_edition: boolean;
	/** The book's published locales (en-modern excluded) — for hreflang on the
	 * chapter page. Chapter counts match across a book's translations. */
	available_languages: string[];
	prev: ChapterNav | null;
	next: ChapterNav | null;
	/**
	 * The passages this chapter treats, for the scripture index at its foot.
	 * `page` is null when the citation floor withheld a page for that
	 * reference — the server owns the floor, so only the server can say what is
	 * linkable. English chapters only; optional so an API running behind this
	 * build simply renders no row.
	 */
	scripture_refs?: { ref: string; page: ScripturePageRef | null }[];
}

/** Where a cited reference's scripture page lives, when one exists. */
export interface ScripturePageRef {
	book: string;
	chapter: number;
	verse: number | null;
}

export interface Language {
	code: string;
	name: string;
	native_name: string;
	/** Right-to-left script — the reader flips direction for these. */
	rtl?: boolean;
	/** English: the language content is authored in. */
	is_source?: boolean;
	/** Registry lifecycle: 'draft' | 'translating' | 'live'. */
	status?: string;
}

export interface ChapterHit {
	type: 'chapter';
	book_slug: string;
	book_title: string;
	author_name: string;
	chapter_order: number;
	chapter_title: string;
	/** The book's cover, so a passage carries the same visual anchor as its book. */
	cover_url: string;
	cover_color: string;
	snippet: string;
	/** Publish date (YYYY-MM-DD) for the "newest" sort; "" if unknown. */
	date: string;
}

export interface SermonHit {
	type: 'sermon';
	sermon_slug: string;
	sermon_title: string;
	author_name: string;
	scripture_ref: string;
	snippet: string;
	/** Publish date (YYYY-MM-DD) for the "newest" sort; "" if unknown. */
	date: string;
}

export interface AuthorHit {
	type: 'author';
	author_slug: string;
	author_name: string;
	/** May be "" — the row reads fine without one, so no placeholder is drawn. */
	photo_url: string;
	snippet: string;
	/** Publish date (YYYY-MM-DD) for the "newest" sort; "" if unknown. */
	date: string;
}

export interface BookHit {
	type: 'book';
	book_slug: string;
	book_title: string;
	author_name: string;
	cover_url: string;
	/** Dominant cover colour, filling the reserved box before/instead of the image. */
	cover_color: string;
	snippet: string;
	/** Publish date (YYYY-MM-DD) for the "newest" sort; "" if unknown. */
	date: string;
}

export interface TopicHit {
	type: 'topic';
	topic_slug: string;
	topic_title: string;
	snippet: string;
	/** Publish date (YYYY-MM-DD) for the "newest" sort; "" if unknown. */
	date: string;
}

export interface PlanHit {
	type: 'plan';
	plan_slug: string;
	plan_title: string;
	snippet: string;
	/** Publish date (YYYY-MM-DD) for the "newest" sort; "" if unknown. */
	date: string;
}

export interface ArticleHit {
	type: 'article';
	article_slug: string;
	/** The article's on-page headline (`h1`) — the display title. */
	article_title: string;
	/** Excerpt of the standfirst; an article carries no author or cover. */
	snippet: string;
	/** Publish date (YYYY-MM-DD) for the "newest" sort; "" if unknown. */
	date: string;
}

export interface ScriptureHit {
	type: 'scripture';
	/** Book slug for the `/scripture/<book>/<chapter>[/<verse>]` link. */
	book_slug: string;
	chapter: number;
	/** A specific verse, or null for a whole-chapter page. */
	verse: number | null;
	/** The human label the row shows — "Romans 8:28" / "Romans 8". */
	reference: string;
	/** Always "" — a scripture page is an aggregation, with no prose of its own. */
	snippet: string;
	/** Always "" — a scripture page has no date to sort by. */
	date: string;
}

export type SearchHit =
	| ChapterHit
	| SermonHit
	| AuthorHit
	| BookHit
	| TopicHit
	| PlanHit
	| ArticleHit
	| ScriptureHit;

export type SearchType = SearchHit['type'];
export type SearchSort = 'relevance' | 'title' | 'newest';

export interface SearchResponse {
	query: string;
	results: SearchHit[];
	/** A "did you mean" term when the query found nothing (fuzzy-matched). */
	suggestion?: string;
	/**
	 * How many matches EXIST per type, which is not how many `results` holds:
	 * the merged list is capped per type so no one kind crowds out the others.
	 * Absent types have no matches at all.
	 */
	totals?: Partial<Record<SearchType, number>>;
	/** True where counting stopped at the server's ceiling — show "N+". */
	totals_capped?: Partial<Record<SearchType, boolean>>;
	/** Rows per "show more" page. */
	page_size?: number;
	/**
	 * The shelf this search was narrowed to, resolved server-side so the page can
	 * name it. Present only when `?in=` was sent; **null** when it named a place
	 * that doesn't exist in this language — an empty list under a confident
	 * label would be a lie, so the page says the shelf isn't there.
	 */
	scope?: SearchScope | null;
}

/** A place a search was narrowed to — see `library.search.scope_entry`. */
export interface SearchScope {
	kind: 'author' | 'topic' | 'book';
	slug: string;
	label: string;
}

/** One type's matches, ordered over ALL of them — the "show more" response. */
export interface SearchPageResponse {
	query: string;
	type: SearchType;
	sort: SearchSort;
	offset: number;
	results: SearchHit[];
}

export interface SermonSummary {
	slug: string;
	language: string;
	title: string;
	scripture_ref: string;
	scripture_book: string | null;
	scripture_book_order: number | null;
	/** "In brief" TL;DR (plain text); "" when none has been written yet. */
	summary: string;
	preached_on: string | null;
	word_count: number;
	author: Author;
	/** Published topics this sermon belongs to (for the shelf's topic filter). */
	topics: TopicChip[];
	/** When the sermon was added to Ochorus (ISO) — powers the "recent" feed. */
	created_at: string;
	/** Last modification (ISO) — the sitemap's `<lastmod>`; see BookSummary. */
	updated_at?: string;
}

/** Adjacent sermon in the author's corpus, for prev/next navigation. */
export interface SermonNeighbour {
	slug: string;
	title: string;
}

export interface Sermon extends SermonSummary {
	body_html: string;
	source_type: SourceType;
	source_url: string;
	/** Free-text rights/credit note. Blank for a public-domain sermon (the page
	 * shows its generic public-domain line); set for one used by permission,
	 * where it replaces that line so the sermon is never mislabelled. */
	attribution?: string;
	author_name: string;
	author_slug: string;
	author_photo: string;
	/** Previous / next sermon by the same author (shelf order); null at the ends. */
	prev: SermonNeighbour | null;
	next: SermonNeighbour | null;
	/** Distinct passages the sermon engages (its text + body citations). */
	scripture_refs: string[];
	/** Reference → `/scripture/<book>/<chapter>/` page URL, for the refs whose
	 * chapter cleared the scripture-graph floor. The chip row links there (a
	 * crawlable internal link) and falls back to search for refs not present. */
	scripture_links: Record<string, string>;
	/** Answered study questions (plain text), shown as a "Questions for
	 * reflection" section and emitted as FAQPage JSON-LD. Empty = none written. */
	study_questions: { question: string; answer: string }[];
	difficulty: Difficulty;
	/** Topical shelves this sermon belongs to (localized), for cross-links. */
	topics: TopicChip[];
	/** Content locales this sermon is published in (sorted, en-modern excluded)
	 * — the only locales an hreflang alternate should point at (per-language
	 * rows, no English fallback). */
	available_languages: string[];
	/**
	 * How many reviewed quotations this sermon's author has — the page shows a
	 * "Quotes from {author}" link when it is non-zero (English only, as the quote
	 * pages are). Optional so an API running behind this build simply omits it.
	 */
	author_quote_count?: number;
}

export interface AuthorBio {
	slug: string;
	name: string;
	bio: string;
	photo_url: string;
	birth_year: number | null;
	death_year: number | null;
	book_count: number;
	sermon_count: number;
	/** A full long-form biography exists (vs. a one-line stub). */
	has_long_bio: boolean;
}

/** What `AuthorTile` draws — see `CoverBook`. A field the tile starts reading
 *  goes in this list, and the home snapshot then carries it too. */
export const AUTHOR_TILE_KEYS = ['slug', 'name', 'photo_url', 'book_count'] as const;
export type AuthorTileData = Pick<AuthorBio, (typeof AUTHOR_TILE_KEYS)[number]>;

/** A writer's dates as displayed: "1843–1919", or "b. 1938" when there is no
 * death year — a bare "1938–" reads as a typo rather than as "still living".
 * Empty when the birth year is unknown, so callers can drop the whole element.
 *
 * Shared because the same lifespan appears on the biographies list, the author
 * page (twice) and a book's byline; inlined, the four drifted apart.
 * `bornLabel` is passed in because translation lives in the component layer.
 */
export const formatLifespan = (
	birth: number | null,
	death: number | null,
	bornLabel: string
): string => (!birth ? '' : death ? `${birth}–${death}` : `${bornLabel} ${birth}`);

/** Whether the "Full life" badge/filter still discriminates the roster: the
 * share of writers with a full-length bio sits in a middle band. Below it the
 * badge is on almost no card; above it on almost every card (English is ~98%) —
 * either way it is noise, not signal. `has_long_bio` is per-language, so this
 * self-tunes per locale. Judge it over the WHOLE locale roster, not a slice, so
 * a card's badge doesn't flicker between the index and an era page.
 *
 * Shared because the biographies index and the per-era pages both need it, and
 * the band literals must live in exactly one place. */
export const fullLifeDiscriminates = (authors: AuthorBio[]): boolean => {
	if (!authors.length) return false;
	const share = authors.filter((a) => a.has_long_bio).length / authors.length;
	return share >= 0.05 && share <= 0.85;
};

/** A book this person is found IN but did not write, with the role they play. */
export interface AppearsInBook extends BookSummary {
	role: PersonRole;
}

export interface AuthorDetail extends AuthorBio {
	bio_html: string;
	/** How the bio in the requested language got here — badge an unreviewed AI
	 * translation. "public_domain" for the source-language original (no badge).
	 * Optional for the same prerender-before-API reason as Chapter.source_type. */
	bio_source_type?: SourceType;
	books: BookSummary[];
	sermons: SermonSummary[];
	/** Topical shelves this author appears in (via their books/sermons). */
	topics: TopicChip[];
	/**
	 * Books this person is found IN but did not write (the reverse of a book's
	 * featured_people) — books they wrote are under `books`. Optional so an API
	 * running behind this build simply renders no section.
	 */
	appears_in?: AppearsInBook[];
	/**
	 * Articles ABOUT this person — the guides to their books and the essays whose
	 * Read-next funnel names them (see `articles_for_author`). Per-language like
	 * the rest of the page, as a book's `guides` is: a locale with translated
	 * articles gets those, one without gets `[]` and no section. Optional so an
	 * API running behind this build omits it cleanly.
	 */
	articles?: ArticleLink[];
	/** How many REVIEWED quotations this author has; 0 means no quote page. */
	quote_count?: number;
	/**
	 * A short question-and-answer set shown at the foot of the page and emitted as
	 * schema.org `FAQPage` markup. Plain-text pairs, in the requested language only
	 * (empty/absent when this locale has no translated set — the no-fallback rule
	 * the bio follows). Optional so an API behind this build renders no Q&A band.
	 */
	faq?: { q: string; a: string }[];
	/**
	 * Authoritative identifiers for this person — Wikipedia, Wikidata — emitted
	 * as schema.org `sameAs`. Empty for the house byline and for contemporary
	 * contributors, and optional besides: an API running behind this build
	 * simply omits the property rather than breaking the markup.
	 */
	same_as?: string[];
	/**
	 * Visible credit for the portrait, shown as a colophon on this page. Set only
	 * when the portrait is a Creative Commons image whose licence requires
	 * attribution; blank/absent for a public-domain portrait or none at all.
	 * Optional so an API behind this build simply renders no credit line.
	 */
	photo_attribution?: string;
	/** The portrait's source page (Wikimedia Commons File:), used as the credit
	 * link. Optional for the same prerender-before-API reason. */
	photo_source_url?: string;
	/**
	 * Life-and-ministry events for the timeline, oldest first. Present only for
	 * the handful of authors that have been curated; everyone else keeps the
	 * plain lifespan bar. Optional for the same prerender-before-API reason.
	 */
	milestones?: Milestone[];
}

/** One dot on the author-page timeline. `key` marks a turning point to emphasise. */
export interface Milestone {
	year: number;
	label: string;
	key?: boolean;
}

/**
 * Fetch a single localized item, falling back to English when it doesn't exist
 * in the requested language. Content is currently English-only, and even once
 * translations exist a missing one should degrade to the original rather than
 * throw — otherwise a reader whose language has no copy of a book gets a raw
 * 500 on the page load instead of readable text.
 */
async function localized<T>(
	path: (lang: string) => string,
	language: string,
	f?: Fetch
): Promise<T> {
	return (await localizedWithLang<T>(path, language, f)).data;
}

/**
 * As `localized`, but reports which language actually answered.
 *
 * The fallback above is deliberately silent, which is right for rendering the
 * text but wrong for describing it: a caller that assumes it got the language it
 * asked for will label English prose as Arabic. That is worse than saying
 * nothing — `lang` drives hyphenation and how a screen reader pronounces the
 * words, so a wrong value actively misleads where a missing one merely
 * abstains. Payloads that carry their own `language` (sermons) should use that;
 * this is for the ones that do not (chapters, biographies).
 */
export async function localizedWithLang<T>(
	path: (lang: string) => string,
	language: string,
	f?: Fetch
): Promise<{ data: T; language: string }> {
	try {
		return { data: await apiFetch<T>(path(language), {}, f), language };
	} catch (e) {
		if (language !== 'en' && e instanceof ApiError && e.status === 404) {
			return { data: await apiFetch<T>(path('en'), {}, f), language: 'en' };
		}
		throw e;
	}
}

export const listBooks = (language = 'en', f?: Fetch) =>
	apiFetch<BookSummary[]>(`/api/library/books/?language=${language}`, {}, f);

export const listAuthors = (language = 'en', f?: Fetch) =>
	apiFetch<AuthorBio[]>(`/api/library/authors/?language=${language}`, {}, f);

/** A series the house imprint's books run in, named in the requested language;
 * `books` holds their slugs in volume order. */
export interface OriginalsSeries {
	slug: string;
	title: string;
	description: string;
	books: string[];
}

/** The /originals shelf: Ochorus' own books in one language, the series they
 * run in, and how many the imprint has in each language (most first). */
export interface OriginalsShelf {
	books: BookSummary[];
	series: OriginalsSeries[];
	languages: { code: string; count: number }[];
}

export const getOriginals = (language = 'en', f?: Fetch) =>
	apiFetch<OriginalsShelf>(`/api/library/originals/?language=${language}`, {}, f);

export const getAuthor = (slug: string, language = 'en') =>
	localized<AuthorDetail>((l) => `/api/library/authors/${slug}/?language=${l}`, language);

/** An author plus the language their biography is actually in — see getChapterWithLang. */
export const getAuthorWithLang = (slug: string, language = 'en', f?: Fetch) =>
	localizedWithLang<AuthorDetail>(
		(l) => `/api/library/authors/${slug}/?language=${l}`,
		language,
		f
	);

export const getBook = async (slug: string, language = 'en', f?: Fetch) =>
	requireFields<BookDetail>(
		`book ${slug}`,
		await localized<BookDetail>((l) => `/api/library/books/${slug}/?language=${l}`, language, f),
		BOOK_FIELDS
	);

export const getChapter = async (slug: string, order: number, language = 'en') =>
	requireFields<Chapter>(
		`chapter ${slug}/${order}`,
		await localized<Chapter>(
			(l) => `/api/library/books/${slug}/chapters/${order}/?language=${l}`,
			language
		),
		CHAPTER_FIELDS
	);

/**
 * A chapter plus the language its body is actually in. The Chapter payload
 * carries no language of its own, and the reader needs the real one for the
 * prose's `lang` attribute — see localizedWithLang.
 */
export const getChapterWithLang = async (
	slug: string,
	order: number,
	language = 'en',
	f?: Fetch
) => {
	// The route the chapter reader actually takes, so this is where the guard
	// has to be: `getChapter` above is the notebook's and the search drawer's
	// path, and guarding only that would leave the reader itself unchecked.
	const res = await localizedWithLang<Chapter>(
		(l) => `/api/library/books/${slug}/chapters/${order}/?language=${l}`,
		language,
		f
	);
	return { ...res, data: requireFields<Chapter>(`chapter ${slug}/${order}`, res.data, CHAPTER_FIELDS) };
};

/** The queries readers search most (aggregate, public). Empty when the log is
 * too sparse — the caller falls back to browse-topic chips. */
export const getPopularSearches = (language = 'en') =>
	apiFetch<{ queries: string[] }>(`/api/library/popular-searches/?language=${language}`);

export const listSermons = (language = 'en', f?: Fetch) =>
	apiFetch<SermonSummary[]>(`/api/library/sermons/?language=${language}`, {}, f);

// Every language the library supports publishing in — not just ones that
// already have content — so the admin import picker can start a new language.
export const listImportLanguages = () =>
	apiFetch<Language[]>('/api/admin/import/languages/');

// Create a name-only stub author from the import flow when the writer isn't in
// the system yet (bio/portrait filled in later). Returns the AuthorBio new row.
export const createAuthor = (name: string) =>
	apiFetch<AuthorBio>('/api/admin/authors/', { method: 'POST', body: JSON.stringify({ name }) });

// Falls back to English on a 404, like getBook/getChapter: a sermon detail view
// filters by (slug, language), so a language-switch on a sermon page or a shared
// /lg/sermons/<slug> link to an untranslated sermon would otherwise dead-end at
// the not-found page instead of degrading to the readable English original.
export const getSermon = async (slug: string, language = 'en', f?: Fetch) =>
	requireFields<Sermon>(
		`sermon ${slug}`,
		await localized<Sermon>((l) => `/api/library/sermons/${slug}/?language=${l}`, language, f),
		SERMON_FIELDS
	);

// --- Articles ----------------------------------------------------------------
// Original devotional/theological writing — no author, no chapters. Per-language
// rows like everything else, and translations exist (fr, lg, es, pt, sw) — do
// not assume English. See backend Article model.

export interface ArticleSummary {
	slug: string;
	language: string;
	/** The on-page headline / display title (the warm H1). */
	h1: string;
	/** SEO <title> text; "" falls back to h1. */
	meta_title: string;
	/** Standfirst — shown under the H1 and used as the meta description. */
	description: string;
	/** Review state — an English original is `public_domain` (no badge); an AI
	 *  translation is `ai_unreviewed` until a native speaker approves it. Shared
	 *  vocabulary with Book/Sermon; the detail page badges it. */
	source_type: SourceType;
	/** Words in the body, derived server-side — feeds `readingTime()`. */
	word_count: number;
	sort_order: number;
	created_at: string;
	/** Last modification (ISO) — the sitemap's `<lastmod>`; see BookSummary. */
	updated_at?: string;
	/** Topics this article belongs to (localized chips) — the index builds its
	 *  filter tabs from these. Empty for an untagged article. */
	topics: TopicChip[];
}

/** A resolved "Read next" link the article funnels the reader to. */
export interface ArticleRelated {
	type: 'book' | 'sermon' | 'author';
	slug: string;
	title: string;
	/** Reader path, trailing-slashed (e.g. `/books/the-life-of-trust/`). */
	url: string;
	/** Thumbnail fields, present per kind so the card renders a cover/portrait,
	 *  not a bare link: a book carries `cover_url` + `cover_color`, an author
	 *  `photo_url`; a sermon carries neither (its tile is a drawn emblem). */
	cover_url?: string;
	cover_color?: string;
	photo_url?: string;
}

export interface Article extends ArticleSummary {
	body_html: string;
	/** Table of contents — the body's `<h2>` sections as `{id, text}` jump
	 *  targets. The ids are already present on the headings in `body_html`
	 *  (injected server-side in one pass), so the page renders this as an
	 *  on-this-page nav and never parses the body itself. */
	toc: { id: string; text: string }[];
	/** The funnel: books / sermons / bios to read next, already resolved to
	 *  titles + URLs server-side (unresolvable references are dropped). */
	related: ArticleRelated[];
	source_url: string;
	// `topics` (the localized chips linking back to the topic pages — the other
	// half of the bidirectional funnel) is inherited from ArticleSummary.
	/** Content locales this article is published in — the only locales an
	 *  hreflang alternate should point at (per-language rows, no fallback). */
	available_languages: string[];
}

export const listArticles = (language = 'en', f?: Fetch) =>
	apiFetch<ArticleSummary[]>(`/api/library/articles/?language=${language}`, {}, f);

// Falls back to English on a 404, like getSermon: an article detail filters by
// (slug, language), so a language switch or a shared /lg link to an
// untranslated article degrades to the English original rather than a 404.
export const getArticle = async (slug: string, language = 'en', f?: Fetch) =>
	requireFields<Article>(
		`article ${slug}`,
		await localized<Article>((l) => `/api/library/articles/${slug}/?language=${l}`, language, f),
		ARTICLE_FIELDS
	);

export const search = (q: string, language = 'en', scope = '') => {
	const params = new URLSearchParams({ q, language });
	if (scope) params.set('in', scope);
	return apiFetch<SearchResponse>(`/api/library/search/?${params}`);
};

/**
 * Tell the server a search result was opened — anonymous, fire-and-forget.
 *
 * The only signal that separates "the search found forty things" from "the
 * search found the thing". `position` is the 1-based rank in the list the
 * reader was actually shown.
 */
export const recordSearchClick = (
	query: string,
	type: SearchType,
	position: number,
	language = 'en'
) =>
	// The language rides in the query string because that is the only place the
	// server reads it from (`language_from_request`). Posting without it recorded
	// every click as English, which would have made the first per-language
	// click-through report read as "nobody but English readers finds anything".
	apiFetch<void>(`/api/library/search-click/?language=${encodeURIComponent(language)}`, {
		method: 'POST',
		body: JSON.stringify({ query, type, position })
	});

/**
 * More of ONE type, ordered over every match rather than over the page the
 * merged search happened to return. Sorting is the server's job for exactly
 * that reason — see library/search.py `page_by_type`.
 */
export const searchPage = (
	q: string,
	language: string,
	type: SearchType,
	opts: { offset?: number; sort?: SearchSort; scope?: string } = {}
) => {
	const params = new URLSearchParams({ q, language, type });
	if (opts.offset) params.set('offset', String(opts.offset));
	if (opts.sort && opts.sort !== 'relevance') params.set('sort', opts.sort);
	// Same scope the merged list used, or "show more" would page out of the shelf.
	if (opts.scope) params.set('in', opts.scope);
	return apiFetch<SearchPageResponse>(`/api/library/search/?${params}`);
};

export interface PlanSummary {
	slug: string;
	language: string;
	title: string;
	description: string;
	day_count: number;
	/** Total words across all the plan's days (for a reading-time estimate). */
	total_words: number;
	/**
	 * Distinct book covers the plan draws from (first-appearance order).
	 * Books only, and the type says so: a plan's days reference `book_slug`
	 * (`PlanDay`), so no sermon can reach this strip.
	 */
	covers: BookTile[];
	/** Where the plan starts, for a "begin here" teaser. Null if day 1's
	 * chapter can't be resolved (e.g. an untranslated book in this locale). */
	day_one: { book_title: string; chapter_title: string } | null;
}

export interface PlanDay {
	day: number;
	book_slug: string;
	chapter_order: number;
	book_title: string;
	chapter_title: string;
	word_count: number;
}

export interface PlanDetail extends PlanSummary {
	days: PlanDay[];
	/** Content locales this plan is published in (sorted) — the only locales an
	 * hreflang alternate should point at. A plan materializes per language only
	 * once its source books are all translated, so this can be a subset. */
	available_languages: string[];
	/** The distinct writers the plan reads through, in first-appearance order —
	 * a link to each author page. Optional so an API predating the field renders
	 * no section (rolling-deploy skew). */
	authors?: { slug: string; name: string }[];
}

export const listPlans = (language = 'en', f?: Fetch) =>
	apiFetch<PlanSummary[]>(`/api/library/plans/?language=${language}`, {}, f);

// English fallback on 404, same reasoning as getSermon: a plan detail view
// filters by (slug, language), so an untranslated plan opened under a locale
// prefix should degrade to English rather than 404.
export const getPlan = (slug: string, language = 'en', f?: Fetch) =>
	localized<PlanDetail>((l) => `/api/library/plans/${slug}/?language=${l}`, language, f);

/**
 * A book in one of the small fanned strips — a plan's, or a topic's.
 *
 * `kind` is what makes `TopicCover` a discriminated union rather than a bag of
 * maybe-fields. Both strips emit it, from the one builder
 * (`serializers._book_cover`), so it is required here: a type that hedged would
 * only be describing a payload neither endpoint sends. Wire data is unchecked
 * either way — a tile arriving without `kind` still falls to the book branch,
 * because `isSermonTile` asks for `'sermon'` rather than assuming.
 */
export interface BookTile {
	kind: 'book';
	slug: string;
	cover_url: string;
	cover_color: string;
	title: string;
}

/**
 * A sermon in a topic's strip. It carries no cover fields because it is not
 * drawn as one: `ShelfCard` renders the round emblem chip a sermon wears
 * everywhere else, resolved from the slug through the frontend art catalogue.
 */
export interface SermonTile {
	kind: 'sermon';
	slug: string;
	title: string;
}

/** A tile in a strip. Topics hold both kinds; plans hold only `BookTile`. */
export type TopicCover = BookTile | SermonTile;

/**
 * Narrows a tile to a sermon.
 *
 * A type predicate rather than a boolean, so the sermon branch gets a `slug`
 * TypeScript knows is there. Without it the call site needs a `?? ''` fallback,
 * which would quietly draw a hash-picked emblem instead of failing.
 */
export const isSermonTile = (cover: TopicCover): cover is SermonTile =>
	cover.kind === 'sermon';

export interface TopicSummary {
	slug: string;
	title: string;
	description: string;
	book_count: number;
	sermon_count: number;
	covers: TopicCover[];
}

/** What a topic chip draws — see `AuthorTileData`. */
export const TOPIC_COUNT_KEYS = ['slug', 'title', 'book_count', 'sermon_count'] as const;
export type TopicCount = Pick<TopicSummary, (typeof TOPIC_COUNT_KEYS)[number]>;

/** An author behind a shelf's works — exactly the shape `PersonCard` renders. */
export interface TopicAuthor {
	slug: string;
	name: string;
	photo_url: string;
	birth_year: number | null;
	death_year: number | null;
}

export interface TopicDetail extends TopicSummary {
	scripture_ref: string;
	scripture_text: string;
	/**
	 * SEO override for the page <title>. The full tag text (already ends in
	 * "— Ochorus"); "" when the shelf has no override, so the reader falls back
	 * to `${title} — Ochorus`. English-owned; "" in a locale until localized.
	 * Optional so an API without the field yet (rolling deploy) reads undefined.
	 */
	seo_title?: string;
	/** SEO override for <meta description>; "" (or absent) → falls back to `description`. */
	meta_description?: string;
	/**
	 * Editorial Questions & Answers about the shelf — hand-authored, grounded in
	 * the topic, per-language via qa_for (English first). The page shows a
	 * "Questions and Answers" section and emits FAQPage JSON-LD; empty/absent =
	 * nothing shown (topics have no derived fallback).
	 */
	qa?: { question: string; answer: string }[];
	/** Locales this shelf exists in — it 404s elsewhere, so hreflang uses this. */
	available_languages: string[];
	books: BookSummary[];
	sermons: SermonSummary[];
	/** Articles about this topic — the bidirectional funnel back to the essays. */
	articles: ArticleSummary[];
	/** Distinct authors behind the shelf's works, curated order. Optional so a
	 *  rolling-deploy skew (an API without the field yet) renders no section. */
	authors?: TopicAuthor[];
	/** Sibling shelves that share books, most-shared first — the lateral "see also". */
	related_topics?: TopicChip[];
}

export const listTopics = (language = 'en', f?: Fetch) =>
	apiFetch<TopicSummary[]>(`/api/library/topics/?language=${language}`, {}, f);

export const getTopic = (slug: string, language = 'en', f?: Fetch) =>
	apiFetch<TopicDetail>(`/api/library/topics/${slug}/?language=${language}`, {}, f);

/** A series with a page in the requested language — the prerender and sitemap list. */
export interface SeriesSummary {
	slug: string;
	title: string;
	book_count: number;
}

/** One series page: see `SeriesDetailView` in the API. */
export interface SeriesDetail {
	slug: string;
	/** Name and description in the requested language (no English fallback). */
	title: string;
	description: string;
	/** False for a collection (no volume numbers, no reading order). */
	ordered: boolean;
	/** Its published books in this language, in volume order. */
	books: BookSummary[];
	/** Languages the series has a page in — for hreflang. */
	available_languages: string[];
}

export const listSeries = (language = 'en') =>
	apiFetch<SeriesSummary[]>(`/api/library/series/?language=${language}`);

/** No English fallback, like `getTopic`: a series with no page here 404s. */
export const getSeries = (slug: string, language = 'en') =>
	apiFetch<SeriesDetail>(`/api/library/series/${slug}/?language=${language}`);

// --- The scripture graph ------------------------------------------------------
// Which passages in the library treat a given verse — the reverse of the
// reader's cross-reference popover, and the one thing here that has no locale
// parameter. Citations are extracted by validating against pythonbible's
// ENGLISH book names, so a Spanish or Swahili edition indexes essentially
// nothing ("Juan 3:16" parses as no reference at all). These pages therefore
// exist in English only, and are advertised that way.

/** One scripture page the build should render — the API decides which qualify. */
export interface ScripturePageEntry {
	book: string;
	book_title: string;
	book_order: number;
	chapter: number;
	/** null for a whole-Bible-chapter page. */
	verse: number | null;
	citing_count: number;
}

/** A library passage that cites the reference this page is about. */
export interface CitingPassage {
	book_slug: string;
	book_title: string;
	author_name: string;
	author_slug: string;
	chapter_order: number;
	chapter_title: string;
	/** The reference AS PRINTED in that book ("Rom. viii. 28"), not normalised. */
	ref: string;
	/** Excerpt centred on the citation, matches wrapped in the search markers. */
	excerpt: string;
}

export interface ScripturePage {
	reference: string;
	book: { slug: string; title: string; order: number };
	chapter: number;
	verse: number | null;
	version: string;
	/** Total citing chapters — NOT the length of `passages`, which is capped. */
	citing_count: number;
	passages: CitingPassage[];
	passages_shown: number;
	/** Verse pages only: the ASV text of the verse. */
	text?: string;
	/**
	 * Chapter pages only: the verses the library actually treats, most-cited
	 * first. `has_page` says whether that verse cleared the (higher) verse floor
	 * and so has a page to link to — the floor lives on the server, so only the
	 * server can answer it.
	 */
	verses?: { number: number; text: string; citing_count: number; has_page: boolean }[];
}

export const listScripturePages = (f?: Fetch) =>
	apiFetch<ScripturePageEntry[]>('/api/library/scripture/pages/', {}, f);

export const getScripturePage = (book: string, chapter: number, verse?: number, f?: Fetch) =>
	apiFetch<ScripturePage>(
		`/api/library/scripture/${book}/${chapter}/` + (verse ? `${verse}/` : ''),
		{},
		f
	);

/**
 * The reader-facing scripture page URL — `/scripture/<book>/<chapter>/` with a
 * trailing `<verse>/` for a verse page. One place for the shape the search hit
 * and the command palette both link to; `null`/`0` verse means the whole chapter.
 */
export const scripturePageHref = (book: string, chapter: number, verse: number | null): string =>
	`/scripture/${book}/${chapter}/` + (verse ? `${verse}/` : '');

// --- Quotes -------------------------------------------------------------------
// Sourced quotations, by author. English-only for the same reason the scripture
// graph is: they are lifted from the English works, and the citation names an
// English chapter. Every card carries its source — that is the product, and the
// one thing the unattributed aggregators cannot copy.

export interface QuoteSource {
	kind: 'chapter' | 'sermon';
	slug: string;
	/** Chapter title, or the sermon's own title. */
	title: string;
	/** The work: the book's title, or the sermon's. */
	work: string;
	/** Chapter order; null for a sermon. */
	order: number | null;
	/** The book's own hue, for the group heading. "" for a sermon. */
	cover_color: string;
}

export interface Quote {
	slug: string;
	text: string;
	/** Index among the body's top-level children — the reader's `?p=` unit. */
	paragraph: number;
	source: QuoteSource;
}

/** A theme the author has enough quotes on to earn a page — a chip on the author page. */
export interface QuoteTopicChip {
	slug: string;
	title: string;
	count: number;
}

export interface QuotePage {
	author: { slug: string; name: string; photo_url: string; birth_year: number | null };
	/** The themes this author has a deep-enough page on ("on Prayer" chips). */
	topics: QuoteTopicChip[];
	/**
	 * In READING ORDER — books before sermons, then each work from its first
	 * chapter to its last. Consecutive quotations therefore share a work, which
	 * is what lets the page group them (and, per STYLE_GUIDE §5, what earns the
	 * group its hue). Do not re-sort without regrouping.
	 */
	quotes: Quote[];
}

/** One work's run of quotations — the unit the page renders and tints. */
export interface QuoteGroup {
	work: string;
	kind: 'chapter' | 'sermon';
	/** Book slug for a chapter group; "" for the sermons group. */
	slug: string;
	hue: string;
	/** Anchor id for the jump row. */
	id: string;
	quotes: Quote[];
}

/**
 * Split quotations in reading order into one group per work, with the sermons
 * gathered into a single trailing group.
 *
 * Six sermons carrying nine quotations between them would otherwise be six
 * groups of one or two, which reads as debris rather than structure.
 */
export function groupQuotes(page: QuotePage, eraHue: string): QuoteGroup[] {
	const groups: QuoteGroup[] = [];
	for (const q of page.quotes) {
		const sermon = q.source.kind === 'sermon';
		const work = sermon ? 'Sermons' : q.source.work;
		const last = groups[groups.length - 1];
		if (last && last.work === work) {
			last.quotes.push(q);
			continue;
		}
		groups.push({
			work,
			kind: q.source.kind,
			slug: sermon ? '' : q.source.slug,
			// A sermon has no cover of its own, so its group takes the writer's
			// era hue — the same one their row wears on the sermons index.
			hue: sermon ? eraHue : q.source.cover_color || eraHue,
			id: sermon ? 'sermons' : `w-${q.source.slug}`,
			quotes: [q]
		});
	}
	return groups;
}

/** Authors with at least one REVIEWED quotation — the pages that may be built. */
/** One row of the /quotes index: an author with a reviewed quote page. */
export interface QuoteAuthorSummary {
	slug: string;
	name: string;
	birth_year: number | null;
	/** Blank for authors with no free image; the card falls back to initials. */
	photo_url: string;
	count: number;
	/** The author's shortest reviewed quote — the card's teaser line. "" if none. */
	teaser: string;
	/** Distinct works (books + sermons) the author is quoted from. */
	work_count: number;
}

export const listQuoteAuthors = (f?: Fetch) =>
	apiFetch<QuoteAuthorSummary[]>('/api/library/quotes/', {}, f);

export const getQuotePage = (author: string, f?: Fetch) =>
	apiFetch<QuotePage>(`/api/library/quotes/${author}/`, {}, f);

/** A saved quote as the favorites shelf shows it: the quote plus the author it
 *  belongs to, since that shelf mixes authors and each card must name its own. */
export interface SavedQuote extends Quote {
	author: { slug: string; name: string };
}

/**
 * Resolve stored quote slugs to their cards — the reader's saved-quotes shelf.
 *
 * A quote is favorited by its own slug, but there is no per-quote page and the
 * shelf can hold quotes from any author, so we POST the stored slugs and get
 * back exactly those cards in the same order. Unknown or now-unreviewed slugs
 * are dropped by the server, so a saved quote that was pulled simply falls off
 * the shelf. Called only when there are quote favorites to resolve.
 */
export const resolveQuotes = (slugs: string[]) =>
	slugs.length
		? apiFetch<SavedQuote[]>('/api/library/quotes/resolve/', {
				method: 'POST',
				body: JSON.stringify({ slugs })
			})
		: Promise.resolve([] as SavedQuote[]);

/**
 * Where a quote's card sends the reader: the exact paragraph it came from.
 *
 * TRAILING SLASH BEFORE THE QUERY. Chapter and sermon pages prerender as
 * directory indexes, so the static host serves them at the slashed URL and
 * 301s the bare one to it. Sixty cards linking the bare form is sixty
 * redirects a reader pays for and a crawler follows, which is what
 * `href.test.ts` scans the built output for.
 */
export const quoteHref = (q: Quote): string =>
	q.source.kind === 'sermon'
		? `/sermons/${q.source.slug}/?p=${q.paragraph}`
		: `/books/${q.source.slug}/${q.source.order}/?p=${q.paragraph}`;

/**
 * The landing page of the WORK a quote sits in (not the paragraph) — its title
 * links here, and its JSON-LD names it as the source's `isPartOf.url`. Shares
 * quoteHref's books-vs-sermons root split so the two never drift apart.
 */
export const workHref = (q: Quote): string =>
	q.source.kind === 'sermon' ? `/sermons/${q.source.slug}/` : `/books/${q.source.slug}/`;

// --- Quote themes -------------------------------------------------------------
// "Quotes on Prayer" (every author) and "Andrew Murray Quotes on Prayer" (one).
// A SEPARATE vocabulary from the work-topic shelves under /topics: this files
// the memorable LINES on a theme, not the books about it. English-only, like the
// quotes themselves. Pages are built only above a quote-count threshold (the
// server applies it), so a thin theme simply has no page until it is tagged
// deeper — the doorway shape a quote page must never take (see quote_seed.py).

/** The standalone label ("The Holy Spirit") lowered for the running "Quotes on …" form. */
export const onPhrase = (title: string): string => title.replace(/^(The|A|An) /, (m) => m.toLowerCase());

/**
 * A full citation for a quote where the work is NOT already the heading — the
 * theme pages mix works under one author, so the card must name the work.
 */
export const citeLine = (q: Quote): string =>
	q.source.kind === 'sermon'
		? `${q.source.work} ¶${q.paragraph}`
		: `${q.source.work}, ch. ${q.source.order} ¶${q.paragraph}`;

/**
 * The shorter citation for pages that GROUP by work, so the work is already the
 * heading and the card need only name the chapter/paragraph. Used by the author
 * page and the author-theme page.
 */
export const citeChapter = (q: Quote): string =>
	q.source.kind === 'sermon'
		? `${q.source.work} ¶${q.paragraph}`
		: `Chapter ${q.source.order} ¶${q.paragraph}`;

export const quoteTopicHref = (slug: string): string => `/quotes/topics/${slug}/`;
export const authorTopicHref = (author: string, topic: string): string =>
	`/quotes/${author}/${topic}/`;

/** One card on the /quotes/topics index. */
export interface QuoteTopicSummary {
	slug: string;
	title: string;
	blurb: string;
	count: number;
}

/** The theme's own furniture — heading, blurb and Scripture epigraph. */
export interface QuoteTopicBrief {
	slug: string;
	title: string;
	blurb: string;
	scripture_ref: string;
	scripture_text: string;
}

/** One author's run of quotes on a theme, on the "Quotes on X" page. */
export interface QuoteAuthorGroup {
	author: { slug: string; name: string; birth_year: number | null };
	count: number;
	/** Whether this author has their own "<Author> Quotes on X" page to link to. */
	has_page: boolean;
	quotes: Quote[];
}

/** "Quotes on X" — the theme across every author. */
export interface QuoteTopicPage {
	topic: QuoteTopicBrief;
	/** Grouped by author, alphabetical; each links to that author's own theme page. */
	authors: QuoteAuthorGroup[];
}

/** "<Author> Quotes on X" — one author, one theme, in reading order. */
export interface QuoteAuthorTopicPage {
	author: { slug: string; name: string; photo_url: string; birth_year: number | null };
	topic: QuoteTopicBrief;
	quotes: Quote[];
}

/** Themes deep enough to earn a page — the /quotes/topics index and its prerender list. */
export const listQuoteTopics = (f?: Fetch) =>
	apiFetch<QuoteTopicSummary[]>('/api/library/quote-topics/', {}, f);

export const getQuoteTopicPage = (topic: string, f?: Fetch) =>
	apiFetch<QuoteTopicPage>(`/api/library/quote-topics/${topic}/`, {}, f);

/** Every (author, theme) pair deep enough to earn a page — the prerender list. */
export const listQuoteTopicPages = () =>
	apiFetch<{ author: string; topic: string }[]>('/api/library/quote-topics/pages/');

export const getQuoteAuthorTopicPage = (author: string, topic: string, f?: Fetch) =>
	apiFetch<QuoteAuthorTopicPage>(`/api/library/quotes/${author}/${topic}/`, {}, f);

/**
 * The `CollectionPage` → `ItemList` of `Quotation`s that both single-author
 * quote pages carry (the author page, and the author-theme page). Each quote is
 * a `Quotation` whose `creator` shares the author's `@id` with their /authors
 * Person node — that shared id is what fuses "the person quoted here" with "the
 * person whose life is here" into one entity — and whose `isPartOf` names the
 * work it was sourced from. Returns the object; the caller wraps it in `jsonLd`.
 */
export function quoteCollectionLd(opts: {
	name: string;
	description: string;
	/** Canonical URL of the page carrying the list. */
	url: string;
	authorSlug: string;
	authorName: string;
	/** In the order the page shows them; positions preserve it. */
	quotes: Quote[];
}) {
	const authorUrl = `${SITE_URL}/authors/${opts.authorSlug}/`;
	return {
		'@context': 'https://schema.org',
		'@type': 'CollectionPage',
		name: opts.name,
		description: opts.description,
		url: opts.url,
		about: { '@type': 'Person', '@id': authorUrl, name: opts.authorName, url: authorUrl },
		mainEntity: {
			'@type': 'ItemList',
			numberOfItems: opts.quotes.length,
			itemListElement: opts.quotes.map((q, i) => ({
				'@type': 'ListItem',
				position: i + 1,
				item: {
					'@type': 'Quotation',
					text: q.text,
					creator: { '@id': authorUrl },
					isPartOf: {
						'@type': q.source.kind === 'sermon' ? 'CreativeWork' : 'Book',
						name: q.source.work,
						url: absUrl(workHref(q))
					},
					url: `${SITE_URL}${quoteHref(q)}`
				}
			}))
		}
	};
}

/** The five kinds a reader can file feedback under — mirrors the backend
 *  `FeedbackCategory`. */
export type FeedbackCategory = 'language' | 'content' | 'feature' | 'bug' | 'other';

/** The surface the reader used to file it — mirrors the backend `FeedbackSource`. */
export type FeedbackSource = 'menu' | 'fab' | 'highlight';

/** A piece of reader feedback, with whatever page context the client could
 *  resolve. Signed-in only — the server stamps the submitter and their role. */
export interface FeedbackSubmission {
	category: FeedbackCategory;
	body: string;
	source?: FeedbackSource;
	page_url?: string;
	content_kind?: string;
	content_slug?: string;
	content_language?: string;
	chapter_ref?: string;
	ui_locale?: string;
	// Highlight-to-feedback (source: 'highlight'): the exact selected text (the
	// durable anchor), an optional proposed correction, and the starting block
	// index for a deep-link back to the spot.
	selected_text?: string;
	suggested_text?: string;
	anchor_block?: number;
}

/** File a suggestion. Requires a signed-in reader; the endpoint is throttled. */
export const submitFeedback = (body: FeedbackSubmission) =>
	apiFetch<{ id: number; ok: boolean }>('/api/feedback/', {
		method: 'POST',
		body: JSON.stringify(body)
	});
