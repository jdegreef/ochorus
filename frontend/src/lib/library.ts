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
}

export interface ChapterToc {
	order: number;
	title: string;
	word_count: number;
}

export interface BookDetail extends BookSummary {
	description: string;
	source_url: string;
	pdf_url: string;
	chapters: ChapterToc[];
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
}

export interface SermonHit {
	type: 'sermon';
	sermon_slug: string;
	sermon_title: string;
	author_name: string;
	scripture_ref: string;
	snippet: string;
}

export type SearchHit = ChapterHit | SermonHit;

export interface SearchResponse {
	query: string;
	results: SearchHit[];
}

export interface SermonSummary {
	slug: string;
	language: string;
	title: string;
	scripture_ref: string;
	preached_on: string | null;
	word_count: number;
	author: Author;
}

export interface Sermon extends SermonSummary {
	body_html: string;
	source_url: string;
	author_name: string;
	author_slug: string;
}

export interface AuthorBio {
	slug: string;
	name: string;
	bio: string;
	photo_url: string;
	birth_year: number | null;
	death_year: number | null;
	book_count: number;
}

export interface AuthorDetail extends AuthorBio {
	bio_html: string;
	books: BookSummary[];
	sermons: SermonSummary[];
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

export const listSermons = (language = 'en') =>
	apiFetch<SermonSummary[]>(`/api/library/sermons/?language=${language}`);

export const getSermon = (slug: string, language = 'en') =>
	apiFetch<Sermon>(`/api/library/sermons/${slug}/?language=${language}`);

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
}

export interface PlanDay {
	day: number;
	book_slug: string;
	chapter_order: number;
	book_title: string;
	chapter_title: string;
}

export interface PlanDetail extends PlanSummary {
	days: PlanDay[];
}

export const listPlans = (language = 'en') =>
	apiFetch<PlanSummary[]>(`/api/library/plans/?language=${language}`);

export const getPlan = (slug: string, language = 'en') =>
	apiFetch<PlanDetail>(`/api/library/plans/${slug}/?language=${language}`);

// --- Admin dashboard ---------------------------------------------------------
// Aggregate content stats for the /admin page. Admin-only (see backend
// accounts.permissions); a non-admin request 401s/403s.

export interface AdminSourceTypeCounts {
	public_domain: number;
	ai_reviewed: number;
	ai_unreviewed: number;
}

export interface AdminTotals {
	works: number;
	books: number;
	published_books: number;
	unpublished_books: number;
	chapters: number;
	sermons: number;
	published_sermons: number;
	plans: number;
	published_plans: number;
	authors: number;
	authors_with_bio: number;
	languages: number;
	words: number;
	chapter_words: number;
	sermon_words: number;
}

export interface AdminLanguageStat {
	code: string;
	name: string;
	native_name: string;
	books: number;
	published_books: number;
	chapters: number;
	sermons: number;
	plans: number;
	words: number;
	source_types: AdminSourceTypeCounts;
}

export interface AdminAttention {
	unpublished_books: number;
	unpublished_sermons: number;
	unreviewed_translations: number;
	authors_without_bio: number;
	empty_chapters: number;
}

export interface AdminRecentBook {
	slug: string;
	title: string;
	language: string;
	author: string;
	source_type: SourceType;
	is_published: boolean;
	created_at: string;
}

export interface AdminStats {
	totals: AdminTotals;
	languages: AdminLanguageStat[];
	source_types: AdminSourceTypeCounts;
	author_translations: { total: number; reviewed: number; unreviewed: number };
	attention: AdminAttention;
	recent_books: AdminRecentBook[];
}

export const getAdminStats = () => apiFetch<AdminStats>('/api/admin/stats/');
