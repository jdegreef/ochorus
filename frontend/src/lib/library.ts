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

export const listLanguages = () => apiFetch<Language[]>('/api/library/languages/');

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
	bios: number;
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

// Per-language drill-down: what's translated into a language + the next items
// to work on.

export interface AdminLangBook {
	slug: string;
	title: string;
	author: string;
	chapters: number;
	source_type: SourceType;
	is_published: boolean;
}

export interface AdminLangSermon {
	slug: string;
	title: string;
	author: string;
	word_count: number;
	is_published: boolean;
}

export interface AdminLangPlan {
	slug: string;
	title: string;
	days: number;
	is_published: boolean;
}

export interface AdminLangBio {
	slug: string;
	name: string;
	reviewed: boolean;
}

export interface AdminLangTodo {
	books: { slug: string; title: string; author: string }[];
	sermons: { slug: string; title: string; author: string }[];
	plans: { slug: string; title: string }[];
	bios: { slug: string; name: string }[];
}

export interface AdminLanguageDetail {
	language: Language;
	is_source: boolean;
	english_counts: { books: number; sermons: number; plans: number; bios: number };
	books: AdminLangBook[];
	sermons: AdminLangSermon[];
	plans: AdminLangPlan[];
	bios: AdminLangBio[];
	todo: AdminLangTodo;
}

export const getAdminLanguageDetail = (code: string) =>
	apiFetch<AdminLanguageDetail>(`/api/admin/languages/${encodeURIComponent(code)}/`);

// Translation-coverage matrix: works (rows) × languages (columns). A book cell
// carries its source_type; sermon/plan cells are "present". Missing = absent.

export interface AdminCoverageRow {
	slug: string;
	title: string;
	author?: string;
	cells: Record<string, SourceType | 'present'>;
}

export interface AdminCoverage {
	languages: Language[];
	books: AdminCoverageRow[];
	sermons: AdminCoverageRow[];
	plans: AdminCoverageRow[];
}

export const getAdminCoverage = () => apiFetch<AdminCoverage>('/api/admin/coverage/');

// AI-translation review queue: unreviewed books + author bios, with approve.

export interface ReviewQueueBook {
	slug: string;
	language: string;
	title: string;
	author: string;
	chapters: number;
}

export interface ReviewQueueBio {
	slug: string;
	language: string;
	name: string;
	has_short: boolean;
	has_long: boolean;
}

export interface ReviewQueue {
	books: ReviewQueueBook[];
	bios: ReviewQueueBio[];
}

export const getReviewQueue = () => apiFetch<ReviewQueue>('/api/admin/review-queue/');

export const approveReview = (body: { kind: 'book' | 'bio'; slug: string; language: string }) =>
	apiFetch<{ ok: boolean }>('/api/admin/review-queue/', {
		method: 'POST',
		body: JSON.stringify(body)
	});

// Content audit: quality (book-qa heuristics) + integrity findings. Each check
// is a capped list with a total.

export interface Capped<T> {
	total: number;
	items: T[];
}

export interface AuditChapterFinding {
	book: string;
	language: string;
	order: number;
	title: string;
	word_count?: number;
	avg_words?: number;
	paragraphs?: number;
	starts?: string;
	ends?: string;
}

export interface AdminAudit {
	quality: {
		generic_titles: Capped<AuditChapterFinding>;
		tiny_chapters: Capped<AuditChapterFinding>;
		giant_chapters: Capped<AuditChapterFinding>;
		fragmented: Capped<AuditChapterFinding>;
		missing_dropcap: Capped<AuditChapterFinding>;
		mid_sentence_splits: Capped<AuditChapterFinding>;
		duplicate_titles: Capped<{ book: string; title: string; count: number }>;
	};
	integrity: {
		empty_books: Capped<{ book: string; language: string; title: string; author: string }>;
		empty_chapters: Capped<AuditChapterFinding>;
		order_gaps: Capped<{ book: string; missing: number[]; count: number }>;
		broken_plan_days: Capped<{ plan: string; language: string; day: number; book: string; order: number }>;
	};
}

export const getAdminAudit = () => apiFetch<AdminAudit>('/api/admin/audit/');

// Reading-engagement analytics (aggregate-only).

export interface EngagementOverview {
	readers: number;
	progress_rows: number;
	active_1d: number;
	active_7d: number;
	active_30d: number;
	readers_with_marks: number;
	marked_chapters: number;
	total_users: number;
}

export interface EngagementBook {
	slug: string;
	title: string;
	author: string;
	readers: number;
	finishers?: number;
	chapters?: number;
}

export interface EngagementLang extends Language {
	readers: number;
}

export interface AdminEngagement {
	overview: EngagementOverview;
	most_read: EngagementBook[];
	most_marked: EngagementBook[];
	by_language: EngagementLang[];
	weekly_active: { week: string; readers: number }[];
}

export const getAdminEngagement = () => apiFetch<AdminEngagement>('/api/admin/engagement/');

// Account analytics: sign-up growth, locale/theme split, activation.

export interface AdminUsers {
	total: number;
	with_activity: number;
	dormant: number;
	signups_7d: number;
	signups_30d: number;
	weekly_signups: { week: string; count: number }[];
	by_locale: (Language & { count: number })[];
	by_theme: { theme: string; label: string; count: number }[];
}

export const getAdminUsers = () => apiFetch<AdminUsers>('/api/admin/users/');

// Per-book detail: a canonical work across all its languages.

export interface AdminBookChapter {
	order: number;
	title: string;
	word_count: number;
	flags: string[];
}

export interface AdminBookLang extends Language {
	id: number;
	title: string;
	subtitle: string;
	description: string;
	source_type: SourceType;
	is_published: boolean;
	sort_order: number;
	cover_url: string;
	cover_color: string;
	source_url: string;
	pdf_url: string;
	word_count: number;
	chapters: AdminBookChapter[];
}

export interface AdminBookDetail {
	slug: string;
	title: string;
	author: { name: string; slug: string; id: number };
	languages: AdminBookLang[];
}

export const getAdminBook = (slug: string) =>
	apiFetch<AdminBookDetail>(`/api/admin/books/${encodeURIComponent(slug)}/`);
