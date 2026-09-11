import { apiFetch } from './api';
import type { Language, SearchType, SourceType } from './library-public';

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
	articles: number;
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

// The dashboard's "needs attention" hub: cheap content-health + demand signals
// aggregated across pages. The API returns raw numbers; the page ranks them and
// owns the labels and links (admin is English-only).
export interface AdminAttentionSignals {
	unreviewed_translations: number;
	unpublished_books: number;
	unpublished_sermons: number;
	authors_without_bio: number;
	empty_chapters: number;
	empty_books: number;
	languages_missing_books: { code: string; name: string; sermons: number }[];
	searches: { total_30d: number; zero_30d: number; zero_rate: number };
}

export const getAdminAttention = () =>
	apiFetch<AdminAttentionSignals>('/api/admin/attention/');

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

/** Like a sermon, but authorless; carries source_type so the row can badge an
 *  unreviewed AI translation. */
export interface AdminLangArticle {
	slug: string;
	title: string;
	word_count: number;
	source_type: SourceType;
	is_published: boolean;
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
	/** English articles not yet in this language, highest sort_order first. */
	articles: { slug: string; title: string }[];
}

export interface AdminLanguageDetail {
	language: Language;
	/** Null for a code that has content but no registry row (e.g. en-modern). */
	settings: LanguageSettings | null;
	is_source: boolean;
	english_counts: { books: number; sermons: number; plans: number; bios: number; articles: number };
	books: AdminLangBook[];
	sermons: AdminLangSermon[];
	plans: AdminLangPlan[];
	bios: AdminLangBio[];
	/** Shelves that exist in this language — i.e. that have a title here. */
	topics: { slug: string; title: string }[];
	articles: AdminLangArticle[];
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
	/** Subset of `blocking` that `force` can't override — a launch past these
	 *  guarantees a failed reader build (today: a missing/incomplete UI
	 *  catalogue), so "launch anyway" is refused for them. */
	unforceable: string[];
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
	/** Only on refusal: 'not_ready' (force overrides it) or 'unbuildable' (a hard
	 *  blocker force can't override — see `readiness.unforceable`). `readiness`
	 *  explains why in both cases. */
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

// Adding a language. The row IS the language: the translate_* commands read
// their Bible and glossary from it, so creating one here is what makes the
// work queueable. Created as a draft — creating and launching are separate
// decisions, and launching runs its own checks.

export interface LanguageSettings {
	code: string;
	name: string;
	native_name: string;
	bible_code: string;
	bible_label: string;
	/** Blank for a public-domain Bible, which is most of them. Non-blank means
	 *  the language cannot go live until `bible_attribution` is filled in — see
	 *  the attribution check in backend/library/readiness.py. */
	bible_licence: string;
	/** The credit line readers see in the footer of that locale. */
	bible_attribution: string;
	rtl: boolean;
	glossary: Record<string, string>;
	/** The terms a glossary must cover, in the order the form should show them. */
	glossary_terms: string[];
	missing_glossary_terms: string[];
	/** Defined in backend/library/language_seed.py — the deploy re-asserts it,
	 *  so the admin refuses to edit it rather than let a change be reverted. */
	repo_managed: boolean;
}

export interface NewLanguage {
	code: string;
	name: string;
	native_name: string;
	bible_code: string;
	bible_label: string;
	/** Carried from the suggestion's licence so the obligation is recorded at
	 *  the moment the Bible is chosen, not remembered later. Optional because
	 *  the usual answer is "public domain, nothing owed". */
	bible_licence?: string;
	/** Not collected at create time — the credit line is written on the
	 *  language's settings page, which is also where the readiness failure
	 *  points. Present here because settings PATCHes share this shape. */
	bible_attribution?: string;
	rtl: boolean;
	glossary: Record<string, string>;
}

export interface CreateLanguageResult {
	language: Language;
	/** False when the Bible API couldn't be reached — not a rejection. */
	bible_verified: boolean;
	bible_note: string;
	next_steps: string[];
}

/** What the add-language form needs: the glossary contract and taken codes. */
/** A language worth adding next: everything the form needs, pre-filled. */
export interface LanguageSuggestion {
	code: string;
	name: string;
	native_name: string;
	rtl: boolean;
	bible: string;
	bible_label: string;
	public_domain: boolean;
	licence: string;
	attribution_required: boolean;
	speakers_millions: number;
}

export const getAdminLanguageForm = () =>
	apiFetch<{
		glossary_terms: string[];
		existing: string[];
		/** Best-effort — empty if Take Root's catalogue is unreachable. */
		suggestions: LanguageSuggestion[];
	}>('/api/admin/languages/');

export const createAdminLanguage = (payload: NewLanguage) =>
	apiFetch<CreateLanguageResult>('/api/admin/languages/', {
		method: 'POST',
		body: JSON.stringify(payload)
	});

/** Edit identity. 409 for a repo-defined language; partial, send what changed. */
export const updateAdminLanguageSettings = (
	code: string,
	patch: Partial<Omit<NewLanguage, 'code'>>
) =>
	apiFetch<{
		code: string;
		updated: string[];
		bible_verified: boolean;
		bible_note: string;
		settings: LanguageSettings;
	}>(`/api/admin/languages/${encodeURIComponent(code)}/settings/`, {
		method: 'PATCH',
		body: JSON.stringify(patch)
	});

// Translation job queue: the "Translate" buttons on the language page file
// GitHub issues that a Claude Code worker session processes one at a time.
// State is derived — queued = open issue, in_progress = claimed by a worker;
// a finished job's item simply leaves the todo list once its translation ships.

export type TranslationJobType = 'book' | 'sermon' | 'plan' | 'bio' | 'topic' | 'article';

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

// A matrix column. `queueable` is true only for languages the translation-jobs
// queue accepts (a registered non-English target) — a column can exist for a
// stray content language the registry never adopted, which can't be queued.
export interface AdminCoverageLanguage extends Language {
	queueable: boolean;
	/** Zero-result searches by this language's readers in the last 30 days —
	 * demand its content isn't answering. Optional across the deploy window. */
	unmet_searches?: number;
}

export interface AdminCoverage {
	languages: AdminCoverageLanguage[];
	books: AdminCoverageRow[];
	sermons: AdminCoverageRow[];
	plans: AdminCoverageRow[];
	// Row = author; the English cell is the original Author.bio_html, translated
	// cells carry ai_reviewed / ai_unreviewed.
	bios: AdminCoverageRow[];
}

export const getAdminCoverage = () => apiFetch<AdminCoverage>('/api/admin/coverage/');

// AI-translation review queue: books, sermons and author bios awaiting a
// native-speaker check — filtered, faceted and paged, with mechanical checks
// attached to the visible page.

export interface ReviewFlags {
	tags_match: boolean;
	tag_counts: [number, number];
	ratio: number | null;
	band: [number, number] | null;
	ratio_in_band: boolean | null;
	quote_style: string;
	quote_style_consistent: boolean;
}

export interface ReviewNoteRef {
	reference: string;
	block_index: number | null;
	status: string;
}

export interface ReviewOutcome {
	outcome: 'approved' | 'needs_work';
	note: string;
	reviewer: string;
	decided_at: string;
}

export type ReviewKind = 'book' | 'sermon' | 'bio';

export interface ReviewItem {
	kind: ReviewKind;
	slug: string;
	language: string;
	title: string;
	author: string;
	chapters: number | null;
	words: number | null;
	scripture_ref: string;
	has_short?: boolean;
	has_long?: boolean;
	created_at: string;
	flagged: boolean;
	/** Whether the pipeline recorded ANY scripture notes. Absence is not safety. */
	notes_recorded: boolean;
	notes: {
		mined: number;
		self_rendered: number;
		/** How many of this translation's verses already carry a decision. */
		settled: number;
		references: ReviewNoteRef[];
	};
	provenance: { job_issue: number | null; pull_request: number | null } | null;
	outcome: ReviewOutcome | null;
	flags?: ReviewFlags | null;
}

export interface ReviewQueue {
	results: ReviewItem[];
	total: number;
	filtered: number;
	flagged_total: number;
	needs_work_total: number;
	page: number;
	pages: number;
	page_size: number;
	facets: { language: Record<string, number>; kind: Record<string, number> };
	/**
	 * Language code → its English name, from the `Language` registry.
	 *
	 * Served rather than held as a map here because an admin can add a language
	 * without a deploy, and its first translations arrive in this very queue —
	 * a frontend map has no way to know that language's name and rendered a bare
	 * code instead. Covers every language present in the queue; a code with no
	 * registry row maps to itself.
	 */
	language_names: Record<string, string>;
}

export interface ReviewQueueParams {
	kind?: string;
	language?: string;
	flagged?: boolean;
	outcome?: string;
	sort?: string;
	page?: number;
}

export const getReviewQueue = (p: ReviewQueueParams = {}) => {
	const q = new URLSearchParams();
	if (p.kind) q.set('kind', p.kind);
	if (p.language) q.set('language', p.language);
	if (p.flagged) q.set('flagged', '1');
	if (p.outcome) q.set('outcome', p.outcome);
	if (p.sort) q.set('sort', p.sort);
	if (p.page && p.page > 1) q.set('page', String(p.page));
	const qs = q.toString();
	return apiFetch<ReviewQueue>(`/api/admin/review-queue/${qs ? `?${qs}` : ''}`);
};

export interface ReviewTarget {
	kind: ReviewKind;
	slug: string;
	language: string;
}

/** Record a decision for one item or a batch. 207 = some rows were held back. */
export const decideReview = (body: {
	items: ReviewTarget[];
	outcome: 'approved' | 'needs_work';
	note?: string;
}) =>
	apiFetch<{
		ok: boolean;
		decided: ReviewTarget[];
		skipped: (ReviewTarget & { reason: string })[];
	}>('/api/admin/review-queue/', { method: 'POST', body: JSON.stringify(body) });

/** Undo a decision, returning the item to the queue. */
export const undoReview = (t: ReviewTarget) => {
	const q = new URLSearchParams({ kind: t.kind, slug: t.slug, language: t.language });
	return apiFetch<{ ok: boolean }>(`/api/admin/review-queue/?${q}`, { method: 'DELETE' });
};

/** One flagged verse: what it says, where, and whether anyone has settled it. */
export interface ReviewVerse {
	reference: string;
	status: string;
	block_index: number | null;
	source_file: string;
	/** The rendered wording, resolved from `block_index`. Null when the text has
	 *  been edited since the note was written and the index no longer lands. */
	text: string | null;
	/** Which chapter it sits in, so the reviewer can open the right one. */
	chapter: number | null;
	review: {
		outcome: VerseOutcome;
		note: string;
		reviewer: string;
		decided_at: string;
	} | null;
}

export type VerseOutcome = 'approved' | 'needs_work';

export interface ReviewDetail {
	kind: ReviewKind;
	slug: string;
	language: string;
	chapter: number | null;
	chapters: { order: number; title: string }[];
	source: { language: string; blocks: string[] };
	target: { language: string; blocks: string[] };
	aligned: boolean;
	block_counts: [number, number];
	notes: ReviewVerse[];
}

/** Settle ONE flagged verse — the unit the review backlog actually moves in. */
export const decideVerse = (
	body: ReviewTarget & { reference: string; outcome: VerseOutcome; note?: string }
) =>
	apiFetch<ReviewVerse['review']>('/api/admin/review-queue/verse/', {
		method: 'POST',
		body: JSON.stringify(body)
	});

/** Undo one verse decision. */
export const undoVerse = (t: ReviewTarget & { reference: string }) => {
	const q = new URLSearchParams({
		kind: t.kind,
		slug: t.slug,
		language: t.language,
		reference: t.reference
	});
	return apiFetch<unknown>(`/api/admin/review-queue/verse/?${q}`, { method: 'DELETE' });
};

export const getReviewDetail = (t: ReviewTarget & { chapter?: number }) => {
	const q = new URLSearchParams({ kind: t.kind, slug: t.slug, language: t.language });
	if (t.chapter) q.set('chapter', String(t.chapter));
	return apiFetch<ReviewDetail>(`/api/admin/review-queue/detail/?${q}`);
};


// Content audit: quality (book-qa heuristics) + integrity findings. Each check
// is a capped list with a total.

export interface Capped<T> {
	total: number;
	items: T[];
	/** Findings a reviewer has accepted as known and removed from `total` — set
	 *  only on the dismissible quality checks. Shown so an emptied check still
	 *  reads as examined, not overlooked. */
	dismissed?: number;
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
		duplicate_titles: Capped<{ book: string; language: string; title: string; count: number }>;
	};
	integrity: {
		empty_books: Capped<{ book: string; language: string; title: string; author: string }>;
		empty_chapters: Capped<AuditChapterFinding>;
		order_gaps: Capped<{ book: string; language: string; missing: number[]; count: number }>;
		broken_plan_days: Capped<{ plan: string; language: string; day: number; book: string; order: number }>;
	};
	/** Content languages that have any finding — computed over the unfiltered
	 *  result, so the picker is stable whatever `language` is selected. */
	languages: string[];
	/** Registry-sourced display names for `languages`, so an edition an admin
	 *  added without a frontend deploy still reads as itself, not a bare code. */
	language_names: Record<string, string>;
	/** The edition this response is filtered to, or '' for all. */
	language: string;
	/** ISO timestamp of the (possibly cached) scan this result was built from —
	 *  the "last run" the page shows. */
	scanned_at: string;
}

/**
 * @param language a content-language code to filter to, or '' for all editions.
 * @param refresh  force a fresh server scan instead of the cached one (Re-run).
 */
export const getAdminAudit = (language = '', refresh = false) => {
	const q = new URLSearchParams();
	if (language) q.set('language', language);
	if (refresh) q.set('refresh', '1');
	const qs = q.toString();
	return apiFetch<AdminAudit>(`/api/admin/audit/${qs ? `?${qs}` : ''}`);
};

/** Identifies one dismissible quality finding: the check plus the finding's
 *  natural key. `ref` is the chapter order (chapter-shaped checks) or the
 *  duplicated title (duplicate_titles) — the same tail the API keys on. */
export interface AuditDismissTarget {
	check: string;
	book: string;
	language: string;
	ref: string;
}

/** Accept one advisory quality finding as known — it drops out of the audit. */
export const dismissAuditFinding = (t: AuditDismissTarget & { note?: string }) =>
	apiFetch<{ ok: boolean; created: boolean }>('/api/admin/audit/dismiss/', {
		method: 'POST',
		body: JSON.stringify(t)
	});

/** Undo an acceptance, returning the finding to the audit. */
export const undoAuditDismissal = (t: AuditDismissTarget) => {
	const q = new URLSearchParams({
		check: t.check,
		book: t.book,
		language: t.language,
		ref: t.ref
	});
	return apiFetch<{ ok: boolean }>(`/api/admin/audit/dismiss/?${q}`, { method: 'DELETE' });
};

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

/** What a reading row's slug names — see WorkKind on the server. */
export type EngagementKind = 'book' | 'sermon' | 'bio';

export interface EngagementWork {
	/** Books, sermons and biographies share the slug column and can collide, so
	 *  a row is only identified by kind AND slug. */
	kind: EngagementKind;
	slug: string;
	title: string;
	author: string;
	readers: number;
	/** Books only: reaching the last chapter means nothing for a single-document
	 *  sermon or bio, so the server sends null rather than a misleading count. */
	finishers?: number | null;
	chapters?: number;
}

export interface EngagementLang extends Language {
	readers: number;
}

export interface AdminEngagement {
	overview: EngagementOverview;
	most_read: EngagementWork[];
	most_marked: EngagementWork[];
	by_language: EngagementLang[];
	weekly_active: { week: string; readers: number }[];
}

export const getAdminEngagement = () => apiFetch<AdminEngagement>('/api/admin/engagement/');

// Account analytics: sign-up growth, locale/theme split, activation.

/** One sign-in provider and how many accounts use it. Counts overlap: an
 *  account with both email and Google is in both rows. `method` "unknown"
 *  collects accounts with no provider recorded yet. */
export interface AdminSignInMethod {
	method: string;
	label: string;
	count: number;
}

/** A single recent sign-up. Admin-only — this is the one place account
 *  analytics names individuals (see the backend AdminUsersView docstring).
 *  `providers` carry their display label from the server, so the client never
 *  keeps its own copy of the provider→label map. */
export interface AdminRecentSignup {
	display_name: string;
	email: string;
	providers: { code: string; label: string }[];
	locale: string;
	joined_at: string;
	last_seen_at: string | null;
}

export interface AdminUsers {
	total: number;
	with_activity: number;
	dormant: number;
	signups_7d: number;
	signups_30d: number;
	weekly_signups: { week: string; count: number }[];
	by_method: AdminSignInMethod[];
	recent: AdminRecentSignup[];
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

/** Zero-result queries for one language — a translation/acquisition worklist. */
export type SearchUnanswered = Language & { total: number; queries: SearchTopQuery[] };

export interface AdminSearchStats {
	overview: {
		'7d': SearchStatsWindow;
		'30d': SearchStatsWindow;
		/** Results opened in 30 days. Rows, not readers — read it as a trend. */
		clicks_30d?: number;
	};
	/**
	 * Queries that found plenty and were never opened — the silent failure the
	 * zero-result list can't see, and often the better content signal.
	 */
	unopened_queries?: SearchTopQuery[];
	top_queries: SearchTopQuery[];
	zero_result_queries: SearchTopQuery[];
	unanswered_by_language: SearchUnanswered[];
	daily: { day: string; searches: number; zero: number }[];
	by_language: (Language & { searches: number; zero: number })[];
}

export const getAdminSearchStats = () => apiFetch<AdminSearchStats>('/api/admin/search-stats/');

/**
 * Where an unanswered query DOES have matches — i.e. what there is to translate.
 * Admin planning only; see `AdminSearchGapView` for why it is a separate call.
 */
export interface AdminSearchGapWork {
	type: TranslationJobType;
	slug: string;
	title: string;
	/** The languages this work was found in — where a translation can come from. */
	languages: string[];
}

export interface AdminSearchGap {
	query: string;
	language: string;
	elsewhere: (Language & { matches: number; by_type: Partial<Record<SearchType, number>> })[];
	/** The specific works behind the matches, deduped — each queueable into `language`. */
	works: AdminSearchGapWork[];
}

export const getAdminSearchGap = (q: string, language: string) =>
	apiFetch<AdminSearchGap>(
		`/api/admin/search-gap/?q=${encodeURIComponent(q)}&language=${encodeURIComponent(language)}`
	);

/**
 * The record of what has been done in the admin — who created a language, moved
 * a readiness bar, took one live, published a document, decided a review.
 *
 * Append-only and read as a window: the endpoint caps what it returns, so
 * `total` can exceed `actions.length` and the page says so rather than implying
 * it is showing everything.
 */
export interface AdminActionRow {
	action: string;
	/** Human phrasing, from the model's own choices so the two can't drift. */
	label: string;
	/** Email; blank only for a DEBUG loopback request with no token. */
	actor: string;
	target: string;
	detail: Record<string, unknown>;
	at: string;
}

export interface AdminActivity {
	/** The full count — a first-page figure; null on a `before` (load-older) page. */
	total: number | null;
	limit: number;
	/** The id to pass as `before` for the next older page, or null when at the end. */
	next_cursor: number | null;
	actions: AdminActionRow[];
}

/**
 * A page of admin actions, newest first. `target` narrows to one object's whole
 * history; `before` is a `next_cursor` from a prior page, to load older rows.
 */
export const getAdminActivity = (opts: { before?: number | null; target?: string } = {}) => {
	const params = new URLSearchParams();
	if (opts.before != null) params.set('before', String(opts.before));
	if (opts.target) params.set('target', opts.target);
	const qs = params.toString();
	return apiFetch<AdminActivity>(`/api/admin/activity/${qs ? `?${qs}` : ''}`);
};
