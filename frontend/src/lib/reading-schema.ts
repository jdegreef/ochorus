/**
 * The single source of truth for the reader's **localStorage contract** — the
 * keys, record shapes, and key format shared by the offline stores
 * (`marks.svelte.ts`, `progress.ts`) and the account mirror (`readingSync.ts`).
 *
 * These three modules read and write the same localStorage entries. Keeping the
 * keys and types here — rather than declaring them independently in each file —
 * means a change to the storage shape can't silently diverge between the offline
 * cache and the sync layer (which would corrupt cross-device reading state).
 * Server (API) types stay in `readingSync.ts`; those are a different contract.
 */

// --- localStorage keys --------------------------------------------------------
export const PROGRESS_KEY = 'ochorus:progress';
export const MARKS_KEY = 'ochorus:marks';
export const ANCHOR_KEY = 'ochorus:anchors';
export const BOOKMARKS_KEY = 'ochorus:bookmarks';
export const PLANS_KEY = 'ochorus:plans';
// A plan's schedule choices — start date, reading days, reminder time — for its
// calendar view: cached here and synced to the account (planSchedules). Not
// progress; wiped with it.
export const PLAN_SCHEDULE_KEY = 'ochorus:plan-schedule';
// The Notebook's own writing — notes and prayers (see journal.ts).
export const JOURNAL_KEY = 'ochorus:journal';
// Journal entries not yet confirmed by the account: id → the updatedAt last
// written. Only these ride the sign-in merge (see readingSync).
export const JOURNAL_DIRTY_KEY = 'ochorus:journal-dirty';
// The day's guided prayer while it is being written: { day, parts }.
export const DAILY_DRAFT_KEY = 'ochorus:daily-draft';
export const FAVORITES_KEY = 'ochorus:favorites';
/** The reader's own Bookshelf shelves — see customShelves.svelte.ts. */
export const SHELVES_KEY = 'ochorus:shelves';
/** Removals (un-hearts, shelf removals) the account hasn't confirmed — see removals.ts. */
export const REMOVALS_KEY = 'ochorus:removals';
// The reading-streak activity log: a JSON array of local 'YYYY-MM-DD' days the
// reader read on. Synced (union-merged) with the account like the rest.
export const ACTIVITY_KEY = 'ochorus:activity';
// When the device last successfully synced with the account (ms epoch, as a
// bare string). Tied to the signed-in session, so it's wiped on sign-out.
export const LAST_SYNC_KEY = 'ochorus:last-sync';
// The reader's measured pace (words over ms), behind every "N min read".
// Device-local — never synced — but the reader's own data all the same: on a
// shared device the next person must not inherit it. See readingPace.svelte.ts.
export const PACE_KEY = 'ochorus:reading-pace';
// The current reading sitting (its active seconds + bounds), buffered here and
// synced to the account so the admin can see time-on-site. Reader's own data —
// wiped on sign-out like the rest. See readingTime.svelte.ts.
export const SESSION_KEY = 'ochorus:reading-session';
// Device-local, never synced: what "Continue reading" needs to draw at
// hydration instead of after a round-trip (see `$lib/resumeBooks`) — the
// summaries of the books the reader has in progress, AND which in-progress
// books and sermons each language lacks. Named for books, its first contents;
// kept rather than renamed, since a new key would orphan every reader's copy
// of this one outside the sign-out wipe. It says what someone is reading, so
// it is wiped on sign-out with the rest.
export const RESUME_BOOKS_KEY = 'ochorus:resume-books';
// Legacy device-local sermon stores, folded into MARKS_KEY / ANCHOR_KEY under
// `sermon:`-prefixed keys when sermons joined the synced reading layer
// (roadmap #10). Kept only so the one-time migrations and the sign-out wipe
// can still find stragglers.
export const LEGACY_SERMON_MARKS_KEY = 'ochorus:sermon-marks';
export const LEGACY_SERMON_ANCHOR_KEY = 'ochorus:sermon-anchor';
// Set when a push to the account failed (offline, a server error): the device
// holds changes the account doesn't. Cleared by the next successful merge,
// which uploads the whole cache. Tied to the session, so wiped with it.
export const SYNC_OWED_KEY = 'ochorus:sync-owed';
// Unsynced reading data set aside when a session ended without the reader
// choosing to (token expiry or revocation), for the SAME account to get back
// at its next sign-in; discarded if anyone else signs in. Deliberately not in
// SIGN_OUT_DATA_KEYS — the sign-out wipe is what writes it — but erased by the
// settings "clear reading data" control. See readingSync.endSession.
export const SYNC_STASH_KEY = 'ochorus:sync-stash';

/**
 * Every key holding the *reader's own data* (positions, highlights, notes,
 * bookmarks, plan progress) — as opposed to device preferences (theme, font,
 * language). These must be wiped on sign-out: on a shared device, whatever is
 * left here gets merged into the NEXT account that signs in.
 */
export const READING_DATA_KEYS = [
	PROGRESS_KEY,
	MARKS_KEY,
	ANCHOR_KEY,
	BOOKMARKS_KEY,
	PLANS_KEY,
	PLAN_SCHEDULE_KEY,
	JOURNAL_KEY,
	JOURNAL_DIRTY_KEY,
	DAILY_DRAFT_KEY,
	FAVORITES_KEY,
	SHELVES_KEY,
	REMOVALS_KEY,
	ACTIVITY_KEY,
	LAST_SYNC_KEY,
	PACE_KEY,
	SESSION_KEY,
	RESUME_BOOKS_KEY,
	LEGACY_SERMON_MARKS_KEY,
	LEGACY_SERMON_ANCHOR_KEY,
	SYNC_OWED_KEY
] as const;

/**
 * The keys wiped when a SESSION ENDS (sign-out button, token expiry, sign-out in
 * another tab). Every reading store now has a server copy — bookmarks joined the
 * synced set (they push on change and ride the merge payload, like
 * marks/progress/favorites) — so a routine sign-out can safely clear them all: on
 * a shared device anything left behind would otherwise merge into the next
 * account that signs in, and the reader's own copy is on the server. Device
 * preferences (theme, font, language) are not in this set; they aren't identity
 * data and deliberately survive.
 */
export const SIGN_OUT_DATA_KEYS = READING_DATA_KEYS;

// --- Work kind ----------------------------------------------------------------
/**
 * What a slug names: a chaptered book, a sermon, an author biography, or an
 * article (the last three are single documents whose one "chapter" is order 1;
 * a bio's slug names the author). Books keep their historical bare storage
 * keys (`slug` / `slug:order`) so nobody's existing cache is invalidated;
 * the others are namespaced with a `sermon:` / `bio:` / `article:` prefix —
 * slugs never contain ':', so the prefixes are unambiguous. The server stores the same
 * distinction as a `kind` column; `readingSync` maps between prefix and column.
 */
export type WorkKind = 'book' | 'sermon' | 'bio' | 'article';
/** Every kind, for guards over data read back from storage or the server. */
export const WORK_KINDS: readonly WorkKind[] = ['book', 'sermon', 'bio', 'article'];

export const SERMON_CHAPTER_ORDER = 1;
/** A biography is a single document too — its one "chapter" is order 1. */
export const BIO_CHAPTER_ORDER = 1;

const SERMON_PREFIX = 'sermon:';
const BIO_PREFIX = 'bio:';
const ARTICLE_PREFIX = 'article:';

/** Storage prefix per namespaced kind — books stay bare (cache compatibility).
 *  One table, so a new kind can't fall through to another kind's prefix. */
const PREFIX: Record<Exclude<WorkKind, 'book'>, string> = {
	sermon: SERMON_PREFIX,
	bio: BIO_PREFIX,
	article: ARTICLE_PREFIX
};

/** Progress-map key for a work (books stay bare — cache compatibility). */
export const workSlugKey = (kind: WorkKind, slug: string) =>
	kind === 'book' ? slug : PREFIX[kind] + slug;

export function parseWorkSlugKey(key: string): { kind: WorkKind; slug: string } {
	for (const [kind, prefix] of Object.entries(PREFIX) as [WorkKind, string][]) {
		if (key.startsWith(prefix)) return { kind, slug: key.slice(prefix.length) };
	}
	return { kind: 'book', slug: key };
}

/** Chapter-scoped key for a work (marks and anchors). */
export const workKey = (kind: WorkKind, slug: string, order: number) =>
	chapterKey(workSlugKey(kind, slug), order);

export function parseWorkKey(
	key: string
): { kind: WorkKind; slug: string; order: number } | null {
	const parsed = parseChapterKey(key);
	if (!parsed) return null;
	const { kind, slug } = parseWorkSlugKey(parsed.slug);
	return { kind, slug, order: parsed.order };
}

/**
 * One-time fold-in of the legacy device-local sermon stores (pre-#10, when
 * sermons lived outside the synced reading layer) into the unified keys.
 *
 * Lives HERE — not in the stores — because every reader of the unified keys
 * must run it first, *including* `readingSync.mergeOnSignIn`: a merge that
 * read `MARKS_KEY` before the fold would upload a payload without the legacy
 * sermon marks, and its response would then overwrite the folded cache —
 * permanently destroying pre-upgrade highlights (a real race: the fold used
 * to run lazily in the stores while the merge fetch was in flight).
 *
 * Idempotent and quota-safe: each legacy key is removed only after the fold
 * has durably written (a full/private-mode storage keeps the legacy copy and
 * retries next read instead of destroying the only copy).
 */
export function migrateLegacySermonState(): void {
	if (typeof localStorage === 'undefined') return;
	try {
		const rawMarks = localStorage.getItem(LEGACY_SERMON_MARKS_KEY);
		if (rawMarks) {
			const store: MarksStore = JSON.parse(localStorage.getItem(MARKS_KEY) || '{}');
			for (const [slug, ms] of Object.entries(
				JSON.parse(rawMarks) as Record<string, Mark[]>
			)) {
				const key = workKey('sermon', slug, SERMON_CHAPTER_ORDER);
				if (!store[key] && Array.isArray(ms) && ms.length) store[key] = { m: ms };
			}
			localStorage.setItem(MARKS_KEY, JSON.stringify(store));
			localStorage.removeItem(LEGACY_SERMON_MARKS_KEY);
		}
	} catch {
		/* corrupt blob or quota failure — keep the legacy copy, retry later */
	}
	try {
		const rawAnchors = localStorage.getItem(LEGACY_SERMON_ANCHOR_KEY);
		if (rawAnchors) {
			const anchors: Record<string, number> = JSON.parse(
				localStorage.getItem(ANCHOR_KEY) || '{}'
			);
			for (const [slug, p] of Object.entries(
				JSON.parse(rawAnchors) as Record<string, number>
			)) {
				const key = workKey('sermon', slug, SERMON_CHAPTER_ORDER);
				if (anchors[key] == null && p > 0) anchors[key] = p;
			}
			localStorage.setItem(ANCHOR_KEY, JSON.stringify(anchors));
			localStorage.removeItem(LEGACY_SERMON_ANCHOR_KEY);
		}
	} catch {
		/* corrupt blob or quota failure — keep the legacy copy, retry later */
	}
}

// --- Highlights & notes -------------------------------------------------------
/**
 * A highlight/note: a character range inside one paragraph of a chapter.
 * `p` = top-level block index in `.reading`; `s`/`e` index that paragraph's text
 * content (layout-independent). `e === -1` means "to the paragraph's end".
 */
export interface Mark {
	id: string;
	p: number;
	s: number;
	e: number;
	note?: string;
	/** Highlight colour key (see HIGHLIGHT_COLORS); absent = the default gold. */
	color?: string;
	/**
	 * The EDITION this mark's offsets were measured against — the content
	 * language, with Modern English as its own edition (`en-modern`). Absent on
	 * anything written before editions were tagged; see `markInEdition`.
	 */
	lang?: string;
	/**
	 * The text this segment covered when it was made (first QUOTE_MAX chars) —
	 * how it is found again after a repair shifts the chapter's text. Absent on
	 * marks made before this was stored. See `$lib/markAnchor`.
	 */
	q?: string;
}

/**
 * An edition is a content language, plus `en-modern` for the Modern English
 * text — the same strings the chapter reader uses to fetch a chapter, so a
 * mark's `lang` and the text it was made against can never drift apart.
 *
 * `{p, s, e}` offsets index one edition's characters. A book's editions share a
 * slug and chapter order (that IS the content model: per-language rows under
 * one slug), so the storage key alone cannot tell them apart — which is how a
 * highlight made in the original text came to be painted across the middle of
 * the modern text's words, and why removing it there deleted the real one.
 */

/**
 * The Modern English edition's content language. Mirrors the backend's single
 * `MODERN_LANGUAGE` constant (library/contemporize.py) — there is exactly one
 * modern edition, and it is English.
 */
export const MODERN_EDITION = 'en-modern';

/** The plain-language edition behind an edition tag (`en-modern` → `en`). */
export const baseEdition = (edition: string): string =>
	edition === MODERN_EDITION ? 'en' : edition;

/**
 * Does this mark belong to `edition`?
 *
 * An untagged mark counts as the BASE edition of whatever is being read, so
 * untagged marks stay visible in the plain-language edition and never bleed
 * into a `-modern` one. No key migration, no rewrite of the reader's own data:
 * marks are separated within the entry they already share.
 *
 * That rule is a guess for one cohort, and knowingly so. The `?edition=modern`
 * reader shipped before marks were tagged, so a highlight made on the modern
 * text in that window is untagged too, and this treats it as the original's —
 * it shows there, mispositioned, and not on the modern text where it was made.
 * Nothing recorded which text those offsets came from, so no rule can place
 * them correctly; this one is chosen because the overwhelming majority of
 * untagged marks predate the modern edition entirely. Marks made from here on
 * carry their edition and are unaffected.
 */
export const markInEdition = (m: Mark, edition: string): boolean =>
	(m.lang ?? baseEdition(edition)) === edition;

/**
 * The highlight palette. Keys are stored on marks (locale-independent) and map
 * to CSS via `mark.range-mark[data-color="…"]` in app.css. The first entry is
 * the default — a mark with no `color` renders as gold, so existing highlights
 * are unaffected.
 */
export const HIGHLIGHT_COLORS = ['gold', 'blue', 'green', 'rose'] as const;
export type HighlightColor = (typeof HIGHLIGHT_COLORS)[number];
export const DEFAULT_HIGHLIGHT: HighlightColor = 'gold';

/** All marks for one chapter. */
export interface ChapterMarks {
	m: Mark[];
	/**
	 * Deletion tombstones: `{ group id -> deleted-at ms }`. A removed mark is
	 * recorded here and sent with every sync so the server (which now unions
	 * marks instead of replacing) can't let a stale device resurrect it. Absent
	 * when the chapter has never had a deletion.
	 */
	d?: Record<string, number>;
}

/** `workKey(kind, slug, order)` -> ChapterMarks. */
export type MarksStore = Record<string, ChapterMarks>;

// --- Bookmarks ----------------------------------------------------------------
/**
 * A saved place in a book: a chapter (`order`) + a paragraph index (`p`) within
 * it, with a short `snippet` and the chapter `title` captured at save time.
 * Distinct from `ProgressRecord` (the single auto-saved resume point) and from
 * `Mark` (a text-range highlight).
 *
 * `title` is a CACHE, not the truth: it is frozen at save time and nothing
 * reconciles it, so a chapter retitled since then leaves it quoting text that
 * no longer exists. Render the live title from the loaded work and fall back to
 * this only when that work isn't loaded — see `TocDrawer` and the notebook.
 * (`marks` and `progress` store no title at all, for exactly this reason; the
 * snapshot earns its place here because a bookmark list has to read offline.)
 */
export interface Bookmark {
	id: string;
	order: number;
	p: number;
	snippet: string;
	title: string;
	at: number;
}

/** book slug -> that book's bookmarks. */
export type BookmarksStore = Record<string, Bookmark[]>;

// --- Reading position ---------------------------------------------------------
/** The resume point for a book: last chapter opened + paragraph within it. */
export interface ProgressRecord {
	order: number;
	paragraph_index: number;
	language: string;
	at: number;
	/**
	 * When the reader FINISHED this work (epoch ms), or null/absent while it is
	 * still in progress. Set by reaching the end of the last chapter (books) or
	 * the single document (sermons, bios), or an explicit "mark as finished".
	 * A finished work drops out of "Continue reading" and onto the finished /
	 * history shelf. Reopening it does not clear this — only an explicit
	 * un-finish does. Synced with the account: finishing unions across devices
	 * (earliest wins), like the streak; see readingSync / reading views.
	 */
	finished_at?: number | null;
	/**
	 * How far through the whole book this place is, 0–100, by words (the
	 * reader's own "N% through" figure, stored when it saves the place). The
	 * lists that show progress have only the book's chapter count, so without
	 * it each surface estimated its own number. Device-local: the account keeps
	 * no percent, so a record synced from another device goes without one until
	 * it is read here. See `workPercent`.
	 */
	pct?: number;
	/**
	 * The furthest chapter the reader has REACHED, where `order` is only the
	 * one last opened: opening the next chapter or reading one to its end
	 * advances it, a peek ahead from the contents or a search doesn't — so
	 * Continue can come back from a peek. Absent on records from before it
	 * existed: read as `order` (see `furthestOf`). Synced; the account keeps
	 * the highest any device reports.
	 */
	furthest?: number;
}

/** The furthest chapter reached; a record from before it was kept, its `order`. */
export function furthestOf(rec: Pick<ProgressRecord, 'order' | 'furthest'>): number {
	return rec.furthest ?? rec.order;
}

/**
 * The chapter "Continue" opens: the one last opened, unless that was a peek
 * past the furthest chapter reached — then back to the furthest. (The reader
 * restores the paragraph there from its own anchor.)
 */
export function resumeOrderOf(rec: Pick<ProgressRecord, 'order' | 'furthest'>): number {
	return Math.min(rec.order, furthestOf(rec));
}

/** `workSlugKey(kind, slug)` -> ProgressRecord. */
export type ProgressMap = Record<string, ProgressRecord>;

// --- Chapter-scoped key -------------------------------------------------------
/** localStorage sub-key for a chapter (marks and anchors both use this). Slugs
 *  never contain ':' so the last ':' separates slug from order. */
export const chapterKey = (slug: string, order: number) => `${slug}:${order}`;

export function parseChapterKey(key: string): { slug: string; order: number } | null {
	const i = key.lastIndexOf(':');
	if (i < 0) return null;
	const order = Number(key.slice(i + 1));
	if (!Number.isFinite(order)) return null;
	return { slug: key.slice(0, i), order };
}
