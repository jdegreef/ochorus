import { apiFetch, ApiError } from './api';

export interface Author {
	slug: string;
	name: string;
	bio: string;
	photo_url: string;
	birth_year: number | null;
	death_year: number | null;
}

export type SourceType = 'public_domain' | 'ai_reviewed' | 'ai_unreviewed';

/** Content-language code of the Modern English edition (not a UI locale). */
export const MODERN_EDITION = 'en-modern';

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
}

export interface Language {
	code: string;
	name: string;
	native_name: string;
}

export interface ChapterHit {
	type: 'chapter';
	book_slug: string;
	book_title: string;
	author_name: string;
	chapter_order: number;
	chapter_title: string;
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
	snippet: string;
	/** Publish date (YYYY-MM-DD) for the "newest" sort; "" if unknown. */
	date: string;
}

export interface BookHit {
	type: 'book';
	book_slug: string;
	book_title: string;
	author_name: string;
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

export interface SearchResponse {
	query: string;
	results: SearchHit[];
	/** A "did you mean" term when the query found nothing (fuzzy-matched). */
	suggestion?: string;
}

export interface SermonSummary {
	slug: string;
	language: string;
	title: string;
	scripture_ref: string;
	scripture_book: string | null;
	scripture_book_order: number | null;
	preached_on: string | null;
	word_count: number;
	author: Author;
	/** When the sermon was added to Ochorus (ISO) — powers the "recent" feed. */
	created_at: string;
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
	/** "In brief" TL;DR (plain text); "" when none has been written yet. */
	summary: string;
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
}

/**
 * Fetch a single localized item, falling back to English when it doesn't exist
 * in the requested language. Content is currently English-only, and even once
 * translations exist a missing one should degrade to the original rather than
 * throw — otherwise a reader whose language has no copy of a book gets a raw
 * 500 on the page load instead of readable text.
 */
async function localized<T>(path: (lang: string) => string, language: string): Promise<T> {
	try {
		return await apiFetch<T>(path(language));
	} catch (e) {
		if (language !== 'en' && e instanceof ApiError && e.status === 404) {
			return apiFetch<T>(path('en'));
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

export const getBook = (slug: string, language = 'en') =>
	localized<BookDetail>((l) => `/api/library/books/${slug}/?language=${l}`, language);

export const getChapter = (slug: string, order: number, language = 'en') =>
	localized<Chapter>((l) => `/api/library/books/${slug}/chapters/${order}/?language=${l}`, language);

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
export const getSermon = (slug: string, language = 'en') =>
	localized<Sermon>((l) => `/api/library/sermons/${slug}/?language=${l}`, language);

export const search = (q: string, language = 'en') =>
	apiFetch<SearchResponse>(
		`/api/library/search/?q=${encodeURIComponent(q)}&language=${language}`
	);

export interface PlanSummary {
	slug: string;
	language: string;
	title: string;
	description: string;
	day_count: number;
	/** Total words across all the plan's days (for a reading-time estimate). */
	total_words: number;
	/** Distinct book covers the plan draws from (first-appearance order). */
	covers: TopicCover[];
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

export interface TopicCover {
	cover_url: string;
	cover_color: string;
	title: string;
}

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
