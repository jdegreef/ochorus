import { apiFetch } from './api';
import type { Language, SourceType } from './library-public';

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
	/** Ranked by how much of the library the author carries — see _bios_todo. */
	bios: { slug: string; name: string; book_count: number; sermon_count: number }[];
	/**
	 * Shelves with no title in this language. NOT truncated like the others: an
	 * untranslated shelf is hidden from the language entirely (topic prose has no
	 * English fallback), so this is a completeness checklist, not a ranked queue.
	 */
	topics: { slug: string; title: string }[];
}

export interface AdminLanguageDetail {
	language: Language;
	is_source: boolean;
	english_counts: { books: number; sermons: number; plans: number; bios: number };
	books: AdminLangBook[];
	sermons: AdminLangSermon[];
	plans: AdminLangPlan[];
	bios: AdminLangBio[];
	/** Shelves that exist in this language — i.e. that have a title here. */
	topics: { slug: string; title: string }[];
	todo: AdminLangTodo;
}

// Readiness: is a language ready to go live, and what's still missing? A
// separate request from the detail payload because the Bible check makes a live
// call to the Take Root API — it shouldn't ride along on every page load.
//
// `status` values: 'pass' | 'fail' | 'unknown' | 'skipped'.
//   - `unknown` means the question couldn't be answered here (no network for the
//     Bible check; the API container can't see the frontend's message
//     catalogues). It does NOT block: interface completeness is enforced at
//     build time, where a live locale with a missing key fails the build.
//   - `skipped` means the threshold is 0, or the check doesn't apply (English).
export interface ReadinessCheck {
	key: string;
	label: string;
	status: 'pass' | 'fail' | 'unknown' | 'skipped';
	detail: string;
	current: number | null;
	required: number | null;
}

export interface LanguageThresholds {
	min_books: number;
	min_sermons: number;
	min_bios: number;
	min_plans: number;
	require_all_topics: boolean;
	require_complete_ui: boolean;
}

export interface AdminLanguageReadiness {
	code: string;
	/** True when no check is failing — `unknown` doesn't count against it. */
	ready: boolean;
	/** Keys of the failing checks, for a one-line summary. */
	blocking: string[];
	status: string;
	checks: ReadinessCheck[];
	thresholds: LanguageThresholds;
}

export const getAdminLanguageReadiness = (code: string) =>
	apiFetch<AdminLanguageReadiness>(
		`/api/admin/languages/${encodeURIComponent(code)}/readiness/`
	);

/** Edit the bar. Partial: send only what changed. 0 disables a count check. */
export const updateAdminLanguageThresholds = (
	code: string,
	patch: Partial<LanguageThresholds>
) =>
	apiFetch<{ code: string; updated: string[]; thresholds: LanguageThresholds }>(
		`/api/admin/languages/${encodeURIComponent(code)}/thresholds/`,
		{ method: 'PATCH', body: JSON.stringify(patch) }
	);

// Going live. Deliberately NOT a status write: the reader is a prerendered
// static site, so the server re-runs the readiness checks, records the launch,
// and triggers the reader's rebuild. `deploy.status` and `launched` are separate
// facts — a language can be recorded live while the rebuild failed — and the UI
// must not merge them into one green tick.
export interface GoLiveResult {
	launched: boolean;
	/** Only on refusal: 'not_ready', with `readiness.blocking` explaining why. */
	reason?: string;
	already_live?: boolean;
	/** True when launched despite failing checks. */
	forced?: boolean;
	went_live_at?: string | null;
	deploy?: { status: 'triggered' | 'not_configured' | 'failed'; detail: string };
	readiness?: AdminLanguageReadiness;
}

/** `force` launches despite failing checks; the result records that it was forced. */
export const goLiveAdminLanguage = (code: string, force = false) =>
	apiFetch<GoLiveResult>(`/api/admin/languages/${encodeURIComponent(code)}/go-live/`, {
		method: 'POST',
		body: JSON.stringify({ force })
	});

/** What actually SHIPPED, as opposed to what was decided — reads the live sitemap. */
export const checkAdminLanguageDeploy = (code: string) =>
	apiFetch<{ status: 'deployed' | 'pending' | 'unknown' | 'n/a'; detail: string }>(
		`/api/admin/languages/${encodeURIComponent(code)}/deploy-check/`
	);

export const getAdminLanguageDetail = (code: string) =>
	apiFetch<AdminLanguageDetail>(`/api/admin/languages/${encodeURIComponent(code)}/`);

// Translation job queue: the "Translate" buttons on the language page file
// GitHub issues that a Claude Code worker session processes one at a time.
// State is derived — queued = open issue, in_progress = claimed by a worker;
// a finished job's item simply leaves the todo list once its translation ships.

export type TranslationJobType = 'book' | 'sermon' | 'plan' | 'bio' | 'topic';

export interface AdminTranslationJob {
	type: TranslationJobType;
	slug: string;
	language: string;
	url: string;
	number: number;
	state: 'queued' | 'in_progress';
	created_at: string;
}

export interface AdminTranslationJobs {
	configured: boolean;
	jobs: AdminTranslationJob[];
}

export const getAdminTranslationJobs = () =>
	apiFetch<AdminTranslationJobs>('/api/admin/translation-jobs/');

export const createAdminTranslationJob = (body: {
	type: TranslationJobType;
	slug: string;
	language: string;
}) =>
	apiFetch<{ job: AdminTranslationJob; created: boolean }>('/api/admin/translation-jobs/', {
		method: 'POST',
		body: JSON.stringify(body)
	});

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

// Search analytics: what readers look for, and what they don't find.

export interface SearchStatsWindow {
	searches: number;
	distinct_queries: number;
	zero_results: number;
	zero_rate: number;
}

export interface SearchTopQuery {
	query: string;
	count: number;
}

export interface AdminSearchStats {
	overview: { '7d': SearchStatsWindow; '30d': SearchStatsWindow };
	top_queries: SearchTopQuery[];
	zero_result_queries: SearchTopQuery[];
	daily: { day: string; searches: number; zero: number }[];
	by_language: (Language & { searches: number; zero: number })[];
}

export const getAdminSearchStats = () => apiFetch<AdminSearchStats>('/api/admin/search-stats/');
