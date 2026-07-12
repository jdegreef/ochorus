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
}

/** All marks for one chapter. */
export interface ChapterMarks {
	m: Mark[];
}

/** `chapterKey(slug, order)` -> ChapterMarks. */
export type MarksStore = Record<string, ChapterMarks>;

// --- Reading position ---------------------------------------------------------
/** The resume point for a book: last chapter opened + paragraph within it. */
export interface ProgressRecord {
	order: number;
	paragraph_index: number;
	language: string;
	at: number;
}

/** book slug -> ProgressRecord. */
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
