import { apiFetch, apiFetchRaw } from './api';
import type { AdminScope } from './adminAccess';
import type { FavoriteKind } from './favorites.svelte';
import type { Language, SearchType, SourceType } from './library-public';
import type { WorkKind } from './reading-schema';

/** Mask an email for display — first char of the local part, then bullets, then
 *  the domain. The single PII-masking rule shared by both admin user pages, so
 *  the list and the detail page can't drift into masking the same address
 *  differently. Reveal is each page's own local state. */
export function maskEmail(email: string): string {
	const at = email.indexOf('@');
	if (at <= 0) return '•••';
	const local = email.slice(0, at);
	return `${local.slice(0, 1)}${'•'.repeat(Math.max(3, local.length - 1))}${email.slice(at)}`;
}

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

// The team / access console — super admin only. Grant/revoke scoped admin
// access; the backend enforces that only super admins can reach these.
export interface TeamMember {
	email: string;
	scopes: AdminScope[];
	roles: string[];
}
export interface AdminTeam {
	members: TeamMember[];
	super_admins: string[];
	roles: string[];
	capabilities: [string, string][];
	verbs: [string, string][];
	languages: string[];
}
export const getAdminTeam = () => apiFetch<AdminTeam>('/api/admin/team/');

/**
 * Fetch the Admin Manual PDF (super-admin only) as an object URL. The endpoint is
 * bearer-gated, so a plain `<a href>` can't reach it — we fetch the blob with the
 * token attached and hand back a `blob:` URL the caller opens in a new tab. The
 * caller owns the URL; revoking it would break the opened tab, so it isn't revoked.
 */
const fetchManualUrl = async (path: string): Promise<string> => {
	const res = await apiFetchRaw(path);
	return URL.createObjectURL(await res.blob());
};

/** The Admin Manual PDF (super admins only). */
export const fetchAdminManualUrl = () => fetchManualUrl('/api/admin/manual/');

/**
 * The Language Admin Manual PDF — readable by any admin (super or a scoped grant);
 * the account menu shows the link only to language admins.
 */
export const fetchLanguageAdminManualUrl = () => fetchManualUrl('/api/admin/language-manual/');

/** Grant a role (or a single capability+verb) to an email, scoped to languages. */
export const grantAdminAccess = (payload: {
	email: string;
	role?: string;
	capability?: string;
	verb?: string;
	languages?: string[];
}) =>
	apiFetch<{ email: string; scopes: AdminScope[] }>('/api/admin/team/', {
		method: 'POST',
		body: JSON.stringify(payload)
	});

/** Revoke a grantee's access — all of it, or just one capability. */
export const revokeAdminAccess = (email: string, capability?: string) => {
	const q = new URLSearchParams({ email });
	if (capability) q.set('capability', capability);
	return apiFetch<{ email: string; revoked: number; scopes: AdminScope[] }>(
		`/api/admin/team/?${q}`,
		{ method: 'DELETE' }
	);
};

export const getAdminAttention = () =>
	apiFetch<AdminAttentionSignals>('/api/admin/attention/');

// Worklists behind two of the attention counts — enumerated so the dashboard
// chips can link to something actionable. Fetched only when the reader opens
// the worklist, so the dashboard's own attention call stays counts-only.
export interface AdminUnpublishedBook {
	slug: string;
	language: string;
	title: string;
	author: string;
	chapters: number;
	words: number;
}
export interface AdminUnpublishedSermon {
	slug: string;
	language: string;
	title: string;
	author: string;
}
export interface AdminUnpublished {
	books: AdminUnpublishedBook[];
	sermons: AdminUnpublishedSermon[];
}

/** Unpublished books and sermons — the worklist for the "unpublished" chips. */
export const getAdminUnpublished = () => apiFetch<AdminUnpublished>('/api/admin/unpublished/');

export interface AdminAuthorWithoutBio {
	slug: string;
	name: string;
	books: number;
	sermons: number;
}

/** Non-imprint authors with an empty bio, most-carrying first. */
export const getAdminAuthorsWithoutBio = () =>
	apiFetch<AdminAuthorWithoutBio[]>('/api/admin/authors-without-bio/');

// Per-language health: one composite score (readiness + coverage + review +
// engagement) per language, ranked, so the dashboard can lead with where the
// next hour of work should go. Read-only and derived — see the backend view.
export type HealthScoreKey = 'readiness' | 'coverage' | 'review' | 'engagement';
export interface AdminLanguageHealth {
	code: string;
	name: string;
	native_name: string;
	rtl: boolean;
	is_source: boolean;
	is_live: boolean;
	/** 0–100 composite. */
	health: number;
	/** Each component in 0–1; the composite's ingredients. */
	scores: Record<HealthScoreKey, number>;
	content: {
		published_books: number;
		unreviewed_books: number;
		sermons: number;
		bios: number;
		plans: number;
		chapters: number;
		words: number;
	};
	readiness: { ready: boolean; blocking: string[] };
	readers: number;
}

export const getAdminLanguageHealth = () =>
	apiFetch<{ source_published_books: number; languages: AdminLanguageHealth[] }>(
		'/api/admin/language-health/'
	);

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

/**
 * Group open translation jobs into per-language, per-type counts — what the
 * dashboard's "+N queued" overlay reads as `counts[language][type]`. Both
 * `queued` and `in_progress` count (neither is live yet). A type with no
 * column on the caller's table (e.g. `topic`) is still tallied but simply
 * never looked up. English never appears — the queue rejects it as a target.
 */
export const countJobsByLanguageType = (
	jobs: readonly AdminTranslationJob[]
): Record<string, Partial<Record<TranslationJobType, number>>> => {
	const counts: Record<string, Partial<Record<TranslationJobType, number>>> = {};
	for (const j of jobs) {
		const lang = (counts[j.language] ??= {});
		lang[j.type] = (lang[j.type] ?? 0) + 1;
	}
	return counts;
};

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
// (Articles: see AdminCoverage.articles.)

export interface AdminCoverageRow {
	slug: string;
	title: string;
	author?: string;
	/** Books only: the series this work belongs to, and its volume. */
	series?: string;
	series_position?: number | null;
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
	// Row = article slug, titled by its h1; no author. The English original is
	// "present", translated cells carry ai_reviewed / ai_unreviewed. Optional
	// across the deploy window (an SPA ahead of the API).
	articles?: AdminCoverageRow[];
	// The series the Books matrix can be narrowed to. Optional across the
	// deploy window, like `articles`.
	series?: { slug: string; title: string }[];
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
	// Maker-checker: an approval recorded by a reviewer who lacks review:approve
	// is provisional (not applied) until an approver confirms it.
	provisional?: boolean;
	confirmed_by?: string;
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

// A period-over-period change for a dashboard stat, or null when there's no
// prior baseline to divide by — a brand-new metric reads "new" rather than a
// fake +100%. Shared by the engagement and users pages so their trend chips
// stay identical (render one with <TrendChip>).
export type Trend = { dir: 'up' | 'down' | 'flat'; text: string } | null;
export const periodTrend = (cur: number, prev: number): Trend => {
	if (prev <= 0) return cur > 0 ? { dir: 'up', text: 'new' } : null;
	const d = Math.round(((cur - prev) / prev) * 100);
	if (d === 0) return { dir: 'flat', text: '0%' };
	return { dir: d > 0 ? 'up' : 'down', text: `${d > 0 ? '+' : ''}${d}%` };
};

// Reading-engagement analytics (aggregate-only).

export interface EngagementOverview {
	readers: number;
	progress_rows: number;
	active_1d: number;
	active_7d: number;
	/** Distinct readers active in the 7 days BEFORE the last 7 — the denominator
	 *  for an honest week-over-week delta, not a bare count. */
	active_7d_prev: number;
	active_30d: number;
	/** The 30 days before the last 30, for the same reason. */
	active_30d_prev: number;
	readers_with_marks: number;
	marked_chapters: number;
	/** Total hearts (Favorites) saved, with a rows-created week-over-week window. */
	hearts: number;
	hearts_7d: number;
	hearts_7d_prev: number;
	total_users: number;
}

/** What a reading row's slug names — see WorkKind on the server. */
export type EngagementKind = 'book' | 'sermon' | 'bio';

/** One row of the reach-vs-depth "Top content" leaderboard: a work with the
 *  four figures that read across a book, sermon or biography at once — how many
 *  reached it, finished it, hearted it, and marked it up. */
export interface EngagementTopRow {
	kind: EngagementKind;
	slug: string;
	title: string;
	author: string;
	readers: number;
	/** Distinct readers who finished (the synced `finished_at` stamp). */
	finishers: number;
	hearts: number;
	/** Distinct readers who highlighted the work. */
	highlighters: number;
}

/** The leaderboard split by kind so each tab holds its own top works. */
export interface EngagementTopContent {
	book: EngagementTopRow[];
	sermon: EngagementTopRow[];
	bio: EngagementTopRow[];
}

export interface EngagementLang extends Language {
	readers: number;
}

/** Time-on-site rollup from reading sittings. `seconds` values are ACTIVE
 *  reading time (foreground, non-idle), so these are real reading totals, not
 *  tab-open time. All zero until the instrumentation has data. */
export interface EngagementTime {
	total_seconds: number;
	sessions: number;
	readers: number;
	avg_session_seconds: number;
	seconds_7d: number;
	readers_7d: number;
	seconds_30d: number;
	readers_30d: number;
}

/** A most-hearted work, keyed on hearts and without a reader/finisher count
 *  (a Favorite is a save, independent of reading). */
export interface EngagementLoved {
	kind: EngagementKind;
	slug: string;
	title: string;
	author: string;
	hearts: number;
}

/** Hearts (Favorites) for one favoritable kind — books, authors, plans,
 *  topics, sermons, articles, quotes. `kind` is the raw FavoriteKind value. */
export interface EngagementHeartKind {
	kind: string;
	count: number;
}

/** One plan's engagement. `returned` = readers who used it past its first day
 *  (ticked ≥ 2 days); `completed` = readers who finished all `length` days. */
export interface EngagementPlanRow {
	slug: string;
	title: string;
	length: number | null;
	started: number;
	returned: number;
	completed: number;
}

/** The reading-plan funnel: overall started → returned → completed, plus a
 *  per-plan breakdown. */
export interface EngagementPlanFunnel {
	started: number;
	returned: number;
	completed: number;
	by_plan: EngagementPlanRow[];
}

/** One chapter's highlight density — distinct readers who marked it up. */
export interface EngagementHeatChapter {
	chapter: number;
	readers: number;
}

/** Per-chapter highlight density for the most-marked book, or null when nothing
 *  has been highlighted yet. Every chapter is present (0 included) so the strip
 *  draws whole; `peak_chapter` is the most-marked one. */
export interface EngagementHeatmap {
	slug: string;
	title: string;
	author: string;
	chapters: EngagementHeatChapter[];
	peak_chapter: number | null;
	peak_readers: number;
}

/** A work whose weekly reach grew — `delta` distinct readers more this week
 *  than the week before. Momentum, not brand-new readers. */
export interface EngagementRisingRow {
	kind: EngagementKind;
	slug: string;
	title: string;
	author: string;
	this_week: number;
	prev_week: number;
	delta: number;
}

export interface AdminEngagement {
	overview: EngagementOverview;
	time: EngagementTime;
	top_content: EngagementTopContent;
	rising: EngagementRisingRow[];
	highlight_heatmap: EngagementHeatmap | null;
	plan_funnel: EngagementPlanFunnel;
	most_loved: EngagementLoved[];
	hearts_by_kind: EngagementHeartKind[];
	by_language: EngagementLang[];
	weekly_active: { week: string; readers: number }[];
}

export const getAdminEngagement = () => apiFetch<AdminEngagement>('/api/admin/engagement/');

// --- Email campaign metrics --------------------------------------------------

export interface EmailMetricRow {
	sent: number;
	delivered: number;
	opens: number;
	clicks: number;
	bounces: number;
	complaints: number;
	open_rate: number;
	click_rate: number;
	bounce_rate: number;
	complaint_rate: number;
}

export interface EmailStepRow extends EmailMetricRow {
	step: string;
}

export interface EmailBroadcastRow extends EmailMetricRow {
	id: number;
	name: string;
}

export interface AdminEmailMetrics {
	overview: EmailMetricRow & { failed: number };
	by_step: EmailStepRow[];
	by_broadcast: EmailBroadcastRow[];
	subscribers: {
		total: number;
		newsletter_opt_in: number;
		unsubscribed: number;
		suppressed: number;
	};
}

export const getAdminEmailMetrics = () =>
	apiFetch<AdminEmailMetrics>('/api/admin/email-metrics/');

// --- Broadcasts (compose / schedule / send) ---------------------------------

export type BroadcastStatus = 'draft' | 'scheduled' | 'sending' | 'sent' | 'canceled';

/** One language's content block for a broadcast (structured, not raw HTML). */
export interface BroadcastBlock {
	heading?: string;
	paragraphs?: string[];
	cta_label?: string;
	cta_path?: string;
	preheader?: string;
	greeting?: string;
}

export interface BroadcastAudience {
	locale?: string;
	signup_variant?: string;
	activity?: 'active_7d' | 'active_30d' | 'lapsed_30d' | 'never_seen';
	has_plan?: boolean;
}

export interface AdminBroadcast {
	id: number;
	name: string;
	status: BroadcastStatus;
	subject: Record<string, string>;
	audience: BroadcastAudience;
	from_address: string;
	scheduled_at: string | null;
	created_at: string;
	updated_at: string;
	locales: string[];
	audience_count: number;
	// detail only:
	content?: Record<string, BroadcastBlock>;
	stats?: EmailMetricRow;
}

export interface BroadcastPayload {
	name?: string;
	subject?: Record<string, string>;
	content?: Record<string, BroadcastBlock>;
	audience?: BroadcastAudience;
	from_address?: string;
}

export const listBroadcasts = () =>
	apiFetch<{ broadcasts: AdminBroadcast[] }>('/api/admin/broadcasts/');

export const getBroadcast = (id: number) =>
	apiFetch<AdminBroadcast>(`/api/admin/broadcasts/${id}/`);

export const createBroadcast = (payload: BroadcastPayload) =>
	apiFetch<AdminBroadcast>('/api/admin/broadcasts/', {
		method: 'POST',
		body: JSON.stringify(payload)
	});

export const updateBroadcast = (id: number, payload: BroadcastPayload) =>
	apiFetch<AdminBroadcast>(`/api/admin/broadcasts/${id}/`, {
		method: 'PATCH',
		body: JSON.stringify(payload)
	});

export const deleteBroadcast = (id: number) =>
	apiFetch<null>(`/api/admin/broadcasts/${id}/`, { method: 'DELETE' });

export const broadcastAction = (
	id: number,
	action: 'send' | 'schedule' | 'cancel' | 'test',
	extra: { scheduled_at?: string } = {}
) =>
	apiFetch<AdminBroadcast & { tally?: Record<string, number>; ok?: boolean; sent_to?: string }>(
		`/api/admin/broadcasts/${id}/action/`,
		{ method: 'POST', body: JSON.stringify({ action, ...extra }) }
	);

export const previewAudience = (audience: BroadcastAudience) =>
	apiFetch<{ count: number }>('/api/admin/broadcasts/audience-preview/', {
		method: 'POST',
		body: JSON.stringify({ audience })
	});

/** Human duration from seconds: "1h 12m", "8m", "45s", "—" for nothing. Shared
 *  by the admin engagement and per-user pages so time reads the same everywhere. */
export function formatDuration(seconds: number): string {
	if (!seconds || seconds < 1) return '—';
	const h = Math.floor(seconds / 3600);
	const m = Math.floor((seconds % 3600) / 60);
	if (h) return m ? `${h}h ${m}m` : `${h}h`;
	if (m) return `${m}m`;
	return `${Math.round(seconds)}s`;
}

// Account analytics: sign-up growth, locale/theme split, activation.

/** One sign-in provider and how many accounts use it. Counts overlap: an
 *  account with both email and Google is in both rows. `method` "unknown"
 *  collects accounts with no provider recorded yet. */
export interface AdminSignInMethod {
	method: string;
	label: string;
	count: number;
}

/** One logged-out sign-up-band arm and how many accounts it drove — the home
 *  page's A/B test. Each account counts once. `targeted` marks the
 *  progress-targeted variant, shown only to readers with local reading, so its
 *  count is NOT comparable head-to-head with the random arms. `variant`
 *  "unknown" collects accounts with none recorded (created before the test, or a
 *  sign-up that carried no variant, e.g. Google). */
export interface AdminSignupVariant {
	variant: string;
	label: string;
	count: number;
	targeted: boolean;
}

/** A single recent sign-up. Admin-only — this is the one place account
 *  analytics names individuals (see the backend AdminUsersView docstring).
 *  `providers` carry their display label from the server, so the client never
 *  keeps its own copy of the provider→label map. */
export interface AdminRecentSignup {
	/** The Supabase UUID — the stable handle the per-user detail page is keyed by. */
	uid: string;
	display_name: string;
	email: string;
	providers: { code: string; label: string }[];
	locale: string;
	joined_at: string;
	last_seen_at: string | null;
}

/** Accounts in one country, derived (approximately) from the browser timezone.
 *  `code` is an ISO alpha-2, or the string "unknown" for the bucket of unmapped
 *  or unreported timezones (same sentinel convention as AdminSignInMethod). */
export interface AdminCountry {
	code: string;
	name: string;
	count: number;
}

/** Accounts reporting one raw IANA timezone. `timezone` "Other" is the folded
 *  tail below the top slots. */
export interface AdminTimezone {
	timezone: string;
	count: number;
}

export interface AdminUsers {
	total: number;
	with_activity: number;
	dormant: number;
	signups_7d: number;
	signups_30d: number;
	/** The immediately preceding window, for a trend delta on the cards. */
	signups_prev_7d: number;
	signups_prev_30d: number;
	weekly_signups: { week: string; count: number }[];
	by_method: AdminSignInMethod[];
	by_signup_variant: AdminSignupVariant[];
	recent: AdminRecentSignup[];
	by_locale: (Language & { count: number })[];
	by_country: AdminCountry[];
	by_timezone: AdminTimezone[];
	by_theme: { theme: string; label: string; count: number }[];
}

export const getAdminUsers = () => apiFetch<AdminUsers>('/api/admin/users/');

// The searchable user directory — every account, paginated, each row linking to
// its per-user detail page. The companion to AdminUsers (which only names the 25
// most recent). Admin-only.

/** One row in the directory. `works` = distinct works opened; `reading_seconds`
 *  = active reading time (see EngagementTime). */
export interface AdminUserRow {
	uid: string;
	display_name: string;
	email: string;
	providers: { code: string; label: string }[];
	locale: string;
	locale_name: string;
	joined_at: string;
	last_seen_at: string | null;
	works: number;
	reading_seconds: number;
}

export type AdminUserSort = 'recent' | 'seen' | 'active' | 'name';

export interface AdminUserDirectory {
	results: AdminUserRow[];
	total: number;
	page: number;
	pages: number;
	page_size: number;
	sort: AdminUserSort;
	q: string;
}

export const getAdminUserDirectory = (
	params: { q?: string; page?: number; sort?: AdminUserSort } = {}
) => {
	const qs = new URLSearchParams();
	if (params.q) qs.set('q', params.q);
	if (params.page && params.page > 1) qs.set('page', String(params.page));
	if (params.sort && params.sort !== 'recent') qs.set('sort', params.sort);
	const s = qs.toString();
	return apiFetch<AdminUserDirectory>(`/api/admin/users/directory/${s ? `?${s}` : ''}`);
};

/** The CSV-export URL for the directory at the given search + sort (all matching
 *  rows). Fetch it with `apiFetchRaw` for the blob — the endpoint + param rules
 *  live here, not inline in the page. */
export const adminUserDirectoryCsvUrl = (params: { q?: string; sort?: AdminUserSort } = {}) => {
	const qs = new URLSearchParams({ fmt: 'csv' });
	if (params.q) qs.set('q', params.q);
	if (params.sort && params.sort !== 'recent') qs.set('sort', params.sort);
	return `/api/admin/users/directory/?${qs}`;
};

// Per-user detail: one reader's profile and activity, keyed by Supabase UUID.
// Admin-only; the companion to the aggregate AdminUsersView. Everything is
// derived on request from the reading tables — see the backend AdminUserDetailView.
//
// The kinds reuse the canonical `WorkKind` / `FavoriteKind` unions (their
// source of truth is the sync schema) rather than re-declaring them, so a new
// kind added there can't silently drift out of step here.

/** A work the reader has open or has finished. `finished_at` is null while in
 *  progress (see reading.ReadingProgress.finished_at). */
export interface UserProgress {
	kind: WorkKind;
	slug: string;
	language: string;
	title: string;
	author: string;
	chapter_order: number;
	paragraph_index: number;
	updated_at: string | null;
	finished_at: string | null;
}

export interface UserFavorite {
	kind: FavoriteKind;
	slug: string;
	/** Resolved display label, or the slug itself when it can't be resolved (quotes). */
	label: string;
	created_at: string | null;
}

export interface UserPlan {
	slug: string;
	title: string;
	started_at: string | null;
	updated_at: string | null;
	done: number;
	/** Days in the plan, or null if the plan row is gone. */
	total_days: number | null;
	pct: number | null;
}

export interface UserHighlight {
	kind: WorkKind;
	slug: string;
	language: string;
	title: string;
	chapter_order: number;
	count: number;
	marks: { text: string; note: string }[];
	updated_at: string | null;
}

export interface UserBookmark {
	kind: WorkKind;
	slug: string;
	title: string;
	chapter_order: number;
	paragraph_index: number;
	snippet: string;
	label: string;
	created_at: string | null;
}

/** One event in the merged, reverse-chron activity timeline. `type` selects the
 *  copy the UI renders; the other fields identify what it points at. */
export interface UserTimelineEvent {
	type: 'read' | 'finished' | 'favorite' | 'bookmark' | 'highlight' | 'plan_started';
	at: string;
	kind: string;
	slug: string;
	language?: string;
	title: string;
	chapter_order?: number;
	snippet?: string;
	count?: number;
}

/** One reading sitting on the per-user page. `seconds` is active reading time. */
export interface UserSession {
	started_at: string | null;
	last_seen_at: string | null;
	seconds: number;
	kind: string;
	slug: string;
	title: string;
}

export interface AdminUserDetail {
	profile: {
		uid: string;
		display_name: string;
		email: string;
		providers: { code: string; label: string }[];
		locale: string;
		locale_name: string;
		theme: string;
		theme_label: string;
		font_scale: number;
		joined_at: string | null;
		last_seen_at: string | null;
		timezone: string;
		/** Approximate, from the browser timezone; null when unmappable. */
		country: { code: string; name: string } | null;
	};
	stats: {
		works_started: number;
		works_finished: number;
		books: number;
		sermons: number;
		bios: number;
		favorites: number;
		highlights: number;
		bookmarks: number;
		plans: number;
		days_read: number;
		streak_current: number;
		streak_longest: number;
		/** Active reading time (see EngagementTime). Zero until instrumented. */
		reading_seconds: number;
		sessions: number;
		avg_session_seconds: number;
	};
	reading: {
		in_progress: UserProgress[];
		finished: UserProgress[];
		last_read: UserProgress | null;
	};
	favorites: UserFavorite[];
	plans: UserPlan[];
	/** Reading sittings, newest first. `title` is blank when the sitting had no
	 *  work context (an older client). */
	sessions: UserSession[];
	highlights: UserHighlight[];
	bookmarks: UserBookmark[];
	/** `today` is the reader's own local date, so the heatmap aligns to the same
	 *  day the streak was judged against (not the admin viewer's timezone). */
	activity: { days: string[]; first: string | null; last: string | null; today: string };
	timeline: UserTimelineEvent[];
}

export const getAdminUser = (uid: string) =>
	apiFetch<AdminUserDetail>(`/api/admin/users/${encodeURIComponent(uid)}/`);

// Per-book detail: a canonical work across all its languages.

export interface AdminBookChapter {
	order: number;
	title: string;
	word_count: number;
	flags: string[];
}

export interface AdminBookLang extends Language {
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

// Content-edit queue: a fix files a GitHub issue a worker turns into a fixture
// PR (a title, a chapter body and an author bio are all fixture-owned prose, not
// live DB writes). Three kinds share the one endpoint — a chapter title/body
// carries an `order`; an author bio does not.
export type ContentEditKind = 'title' | 'body' | 'bio';
export interface ContentEditJob {
	kind: ContentEditKind;
	entity: 'book' | 'author';
	slug: string;
	language: string;
	order: number | null;
	url: string;
	number: number | null;
	state: 'queued' | 'in_progress';
	created_at: string;
}

type FiledJob = { job: ContentEditJob | null; created: boolean };
const fileContentEdit = (body: Record<string, unknown>) =>
	apiFetch<FiledJob>('/api/admin/content-edit-jobs/', {
		method: 'POST',
		body: JSON.stringify(body)
	});

/** File a "retitle this chapter" job; `created` is false if one was already open. */
export const fileRetitleJob = (slug: string, language: string, order: number, title: string) =>
	fileContentEdit({ kind: 'title', slug, language, order, title });

/** File a "revise this chapter's text" job — `note` describes what's wrong. */
export const fileBodyFixJob = (slug: string, language: string, order: number, note: string) =>
	fileContentEdit({ kind: 'body', slug, language, order, note });

/** File a "write / expand this author's bio" job; `note` (optional) says what to
 *  emphasise. Defaults to the English source bio. */
export const fileBioJob = (slug: string, note: string, language = 'en') =>
	fileContentEdit({ kind: 'bio', slug, language, note });

/**
 * Publish or unpublish one language edition of a book. `is_published` is the
 * reader-visibility switch (the public API filters on it), so unpublishing
 * removes the edition from the site immediately. Scoped to one `(slug, language)`
 * row — the caller toggles one edition at a time.
 */
export const setBookPublished = (slug: string, language: string, published: boolean) =>
	apiFetch<{ slug: string; language: string; is_published: boolean }>(
		`/api/admin/books/${encodeURIComponent(slug)}/publish/`,
		{ method: 'POST', body: JSON.stringify({ language, published }) }
	);

// The sermon counterpart to the book detail — one canonical sermon across its
// languages, minus chapters (a sermon is a single body).
export interface AdminSermonLang extends Language {
	title: string;
	scripture_ref: string;
	source_type: SourceType;
	is_published: boolean;
	word_count: number;
	source_url: string;
}
export interface AdminSermonDetail {
	slug: string;
	title: string;
	author: { name: string; slug: string };
	languages: AdminSermonLang[];
}

export const getAdminSermon = (slug: string) =>
	apiFetch<AdminSermonDetail>(`/api/admin/sermons/${encodeURIComponent(slug)}/`);

/** Publish/unpublish one sermon edition — the sibling of setBookPublished. */
export const setSermonPublished = (slug: string, language: string, published: boolean) =>
	apiFetch<{ slug: string; language: string; is_published: boolean }>(
		`/api/admin/sermons/${encodeURIComponent(slug)}/publish/`,
		{ method: 'POST', body: JSON.stringify({ language, published }) }
	);

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

// --- Reader feedback queue ---------------------------------------------------

/** One item in the feedback queue — the backend `Feedback`, serialized. */
export interface FeedbackItem {
	id: number;
	category: string;
	body: string;
	/** Which surface it came from: 'menu' | 'fab' | 'highlight'. */
	source: string;
	status: string;
	submitter_email: string;
	/** '' for an ordinary reader, else e.g. 'language_admin' / 'super_admin'. */
	submitter_role: string;
	page_url: string;
	content_kind: string;
	content_slug: string;
	content_language: string;
	chapter_ref: string;
	ui_locale: string;
	/** Highlight-to-feedback: the quoted selection, an optional proposed
	 *  correction, and the block index for a deep-link back to the spot. */
	selected_text: string;
	suggested_text: string;
	anchor_block: number | null;
	/** How many other shown items flag the same passage (a dedup nudge). */
	similar?: number;
	assignee_email: string;
	admin_note: string;
	duplicate_of: number | null;
	created_at: string;
	updated_at: string;
}

export interface FeedbackQueue {
	items: FeedbackItem[];
	/** Per-status totals, for the filter chips. */
	counts: Record<string, number>;
	total: number;
}

/** The statuses an item can be moved to (NEW is the birth state, never a
 *  target) — mirrors the backend `TRIAGE_STATUSES`. */
export const FEEDBACK_TRIAGE_STATUSES = [
	'triaging',
	'planned',
	'in_progress',
	'done',
	'declined',
	'duplicate'
] as const;

/** GET the feedback queue, optionally filtered by status and category. */
export const getFeedbackQueue = (
	p: { status?: string; category?: string; source?: string } = {}
) => {
	const q = new URLSearchParams();
	if (p.status) q.set('status', p.status);
	if (p.category) q.set('category', p.category);
	if (p.source) q.set('source', p.source);
	const qs = q.toString();
	return apiFetch<FeedbackQueue>(`/api/admin/feedback/${qs ? `?${qs}` : ''}`);
};

/** POST a triage change for one item — only the fields present are applied. */
export const triageFeedback = (
	id: number,
	body: { status?: string; assignee_email?: string; admin_note?: string; duplicate_of?: number | null }
) =>
	apiFetch<FeedbackItem>(`/api/admin/feedback/${encodeURIComponent(String(id))}/`, {
		method: 'POST',
		body: JSON.stringify(body)
	});
