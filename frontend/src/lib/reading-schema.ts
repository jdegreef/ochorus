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
export const FAVORITES_KEY = 'ochorus:favorites';
// The reading-streak activity log: a JSON array of local 'YYYY-MM-DD' days the
// reader read on. Synced (union-merged) with the account like the rest.
export const ACTIVITY_KEY = 'ochorus:activity';
// When the device last successfully synced with the account (ms epoch, as a
// bare string). Tied to the signed-in session, so it's wiped on sign-out.
export const LAST_SYNC_KEY = 'ochorus:last-sync';
// Legacy device-local sermon stores, folded into MARKS_KEY / ANCHOR_KEY under
// `sermon:`-prefixed keys when sermons joined the synced reading layer
// (roadmap #10). Kept only so the one-time migrations and the sign-out wipe
// can still find stragglers.
export const LEGACY_SERMON_MARKS_KEY = 'ochorus:sermon-marks';
export const LEGACY_SERMON_ANCHOR_KEY = 'ochorus:sermon-anchor';

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
	FAVORITES_KEY,
	ACTIVITY_KEY,
	LAST_SYNC_KEY,
	LEGACY_SERMON_MARKS_KEY,
	LEGACY_SERMON_ANCHOR_KEY
] as const;

/**
 * The keys wiped when a SESSION ENDS (sign-out button, token expiry, sign-out in
 * another tab). This is READING_DATA_KEYS *minus* any store that has no server
 * copy: wiping an un-synced store on a routine sign-out would be silent,
 * unrecoverable data loss, not a privacy win.
 *
 * BOOKMARKS_KEY is excluded because bookmarks are not yet synced to the account
 * (unlike marks/progress/favorites, they have no push and aren't in the merge
 * payload) — so a sign-out is the reader's ONLY copy. They stay device-local
 * until an explicit "clear reading data" (which still uses READING_DATA_KEYS).
 * The shared-device tradeoff: a signed-out reader's bookmarks remain visible on
 * that browser; acceptable versus guaranteed loss, and they are never merged
 * into the next account. TODO(review #36): sync bookmarks, then fold this back.
 */
export const SIGN_OUT_DATA_KEYS = READING_DATA_KEYS.filter(
	(k) => k !== BOOKMARKS_KEY
);

// --- Work kind ----------------------------------------------------------------
/**
 * What a slug names: a chaptered book, a sermon, or an author biography (the
 * latter two are single documents whose one "chapter" is order 1; a bio's slug
 * names the author). Books keep their historical bare storage keys
 * (`slug` / `slug:order`) so nobody's existing cache is invalidated; sermons
 * and bios are namespaced with a `sermon:` / `bio:` prefix — slugs never
 * contain ':', so the prefixes are unambiguous. The server stores the same
 * distinction as a `kind` column; `readingSync` maps between prefix and column.
 */
export type WorkKind = 'book' | 'sermon' | 'bio';

export const SERMON_CHAPTER_ORDER = 1;
/** A biography is a single document too — its one "chapter" is order 1. */
export const BIO_CHAPTER_ORDER = 1;

const SERMON_PREFIX = 'sermon:';
const BIO_PREFIX = 'bio:';

/** Progress-map key for a work (books stay bare — cache compatibility). */
export const workSlugKey = (kind: WorkKind, slug: string) =>
	kind === 'book' ? slug : (kind === 'sermon' ? SERMON_PREFIX : BIO_PREFIX) + slug;

export function parseWorkSlugKey(key: string): { kind: WorkKind; slug: string } {
	if (key.startsWith(SERMON_PREFIX)) return { kind: 'sermon', slug: key.slice(SERMON_PREFIX.length) };
	if (key.startsWith(BIO_PREFIX)) return { kind: 'bio', slug: key.slice(BIO_PREFIX.length) };
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

/** The plain-language edition behind an edition tag (`en-modern` → `en`). */
const baseEdition = (edition: string): string => edition.replace(/-modern$/, '');

/**
 * Does this mark belong to `edition`?
 *
 * An untagged mark counts as the BASE edition of whatever is being read. Every
 * such mark predates tagging, and nothing could then create one against the
 * Modern English text under a tag of its own — so untagged marks stay visible
 * in the plain-language edition (losing them would be far worse than the bug)
 * and never bleed into a `-modern` one. No key migration, no rewrite of the
 * reader's own data: marks are separated within the entry they already share.
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
}

/** `workKey(kind, slug, order)` -> ChapterMarks. */
export type MarksStore = Record<string, ChapterMarks>;

// --- Bookmarks ----------------------------------------------------------------
/**
 * A saved place in a book: a chapter (`order`) + a paragraph index (`p`) within
 * it, with a short `snippet` and the chapter `title` captured at save time so
 * the list renders without re-fetching. Distinct from `ProgressRecord` (the
 * single auto-saved resume point) and from `Mark` (a text-range highlight).
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
