import { apiFetch, ApiError } from './api';
import {
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
 * in it. Both AI states count; whether a native speaker has SIGNED OFF on the
 * translation is a separate question, and one only the work's own page answers
 * (see SourceBadge).
 *
 * One function because the test was written out at four call sites, and a fifth
 * (the shelf's own source filter) wrote its negation.
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
	author: Author;
	source_type: SourceType;
	cover_color: string;
	cover_url: string;
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

export interface ChapterToc {
	order: number;
	title: string;
	word_count: number;
}

export interface TopicChip {
	slug: string;
	title: string;
}

/** Relative reading-difficulty badge, computed server-side; null = unjudged. */
export type Difficulty = 'accessible' | 'moderate' | 'advanced' | null;

export interface BookDetail extends BookSummary {
	description: string;
	source_url: string;
	pdf_url: string;
	chapters: ChapterToc[];
	topics: TopicChip[];
	related: BookSummary[];
	difficulty: Difficulty;
	/**
	 * The author's authoritative identifiers (Wikipedia, Wikidata), for the
	 * Person inside this page's Book markup. Only the book DETAIL payload
	 * carries them — a card emits no Person markup.
	 */
	author_same_as?: string[];
	alternate_titles?: string[];
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

export type SearchHit = ChapterHit | SermonHit | AuthorHit | BookHit | TopicHit | PlanHit;

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
	author_name: string;
	author_slug: string;
	author_photo: string;
	/** Previous / next sermon by the same author (shelf order); null at the ends. */
	prev: SermonNeighbour | null;
	next: SermonNeighbour | null;
	/** Distinct passages the sermon engages (its text + body citations). */
	scripture_refs: string[];
	difficulty: Difficulty;
	/** Topical shelves this sermon belongs to (localized), for cross-links. */
	topics: TopicChip[];
	/** Content locales this sermon is published in (sorted, en-modern excluded)
	 * — the only locales an hreflang alternate should point at (per-language
	 * rows, no English fallback). */
	available_languages: string[];
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

export interface AuthorDetail extends AuthorBio {
	bio_html: string;
	books: BookSummary[];
	sermons: SermonSummary[];
	/** Topical shelves this author appears in (via their books/sermons). */
	topics: TopicChip[];
	/** How many REVIEWED quotations this author has; 0 means no quote page. */
	quote_count?: number;
	/**
	 * Authoritative identifiers for this person — Wikipedia, Wikidata — emitted
	 * as schema.org `sameAs`. Empty for the house byline and for contemporary
	 * contributors, and optional besides: an API running behind this build
	 * simply omits the property rather than breaking the markup.
	 */
	same_as?: string[];
}

/**
 * Fetch a single localized item, falling back to English when it doesn't exist
 * in the requested language. Content is currently English-only, and even once
 * translations exist a missing one should degrade to the original rather than
 * throw — otherwise a reader whose language has no copy of a book gets a raw
 * 500 on the page load instead of readable text.
 */
async function localized<T>(path: (lang: string) => string, language: string): Promise<T> {
	return (await localizedWithLang<T>(path, language)).data;
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
	language: string
): Promise<{ data: T; language: string }> {
	try {
		return { data: await apiFetch<T>(path(language)), language };
	} catch (e) {
		if (language !== 'en' && e instanceof ApiError && e.status === 404) {
			return { data: await apiFetch<T>(path('en')), language: 'en' };
		}
		throw e;
	}
}

export const listBooks = (language = 'en') =>
	apiFetch<BookSummary[]>(`/api/library/books/?language=${language}`);

export const listAuthors = (language = 'en') =>
	apiFetch<AuthorBio[]>(`/api/library/authors/?language=${language}`);

export const getAuthor = (slug: string, language = 'en') =>
	localized<AuthorDetail>((l) => `/api/library/authors/${slug}/?language=${l}`, language);

/** An author plus the language their biography is actually in — see getChapterWithLang. */
export const getAuthorWithLang = (slug: string, language = 'en') =>
	localizedWithLang<AuthorDetail>((l) => `/api/library/authors/${slug}/?language=${l}`, language);

export const getBook = async (slug: string, language = 'en') =>
	requireFields<BookDetail>(
		`book ${slug}`,
		await localized<BookDetail>((l) => `/api/library/books/${slug}/?language=${l}`, language),
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
export const getChapterWithLang = async (slug: string, order: number, language = 'en') => {
	// The route the chapter reader actually takes, so this is where the guard
	// has to be: `getChapter` above is the notebook's and the search drawer's
	// path, and guarding only that would leave the reader itself unchecked.
	const res = await localizedWithLang<Chapter>(
		(l) => `/api/library/books/${slug}/chapters/${order}/?language=${l}`,
		language
	);
	return { ...res, data: requireFields<Chapter>(`chapter ${slug}/${order}`, res.data, CHAPTER_FIELDS) };
};

/** The queries readers search most (aggregate, public). Empty when the log is
 * too sparse — the caller falls back to browse-topic chips. */
export const getPopularSearches = (language = 'en') =>
	apiFetch<{ queries: string[] }>(`/api/library/popular-searches/?language=${language}`);

export const listSermons = (language = 'en') =>
	apiFetch<SermonSummary[]>(`/api/library/sermons/?language=${language}`);

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
export const getSermon = async (slug: string, language = 'en') =>
	requireFields<Sermon>(
		`sermon ${slug}`,
		await localized<Sermon>((l) => `/api/library/sermons/${slug}/?language=${l}`, language),
		SERMON_FIELDS
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
}

export const listPlans = (language = 'en') =>
	apiFetch<PlanSummary[]>(`/api/library/plans/?language=${language}`);

// English fallback on 404, same reasoning as getSermon: a plan detail view
// filters by (slug, language), so an untranslated plan opened under a locale
// prefix should degrade to English rather than 404.
export const getPlan = (slug: string, language = 'en') =>
	localized<PlanDetail>((l) => `/api/library/plans/${slug}/?language=${l}`, language);

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

export interface TopicDetail extends TopicSummary {
	scripture_ref: string;
	scripture_text: string;
	/** Locales this shelf exists in — it 404s elsewhere, so hreflang uses this. */
	available_languages: string[];
	books: BookSummary[];
	sermons: SermonSummary[];
}

export const listTopics = (language = 'en') =>
	apiFetch<TopicSummary[]>(`/api/library/topics/?language=${language}`);

export const getTopic = (slug: string, language = 'en') =>
	apiFetch<TopicDetail>(`/api/library/topics/${slug}/?language=${language}`);

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

export const listScripturePages = () =>
	apiFetch<ScripturePageEntry[]>('/api/library/scripture/pages/');

export const getScripturePage = (book: string, chapter: number, verse?: number) =>
	apiFetch<ScripturePage>(
		`/api/library/scripture/${book}/${chapter}/` + (verse ? `${verse}/` : '')
	);

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

export interface QuotePage {
	author: { slug: string; name: string; photo_url: string; birth_year: number | null };
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
export const listQuoteAuthors = () => apiFetch<string[]>('/api/library/quotes/');

export const getQuotePage = (author: string) =>
	apiFetch<QuotePage>(`/api/library/quotes/${author}/`);

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
