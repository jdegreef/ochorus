/**
 * The pure arithmetic behind a reading *sitting* — kept out of the store so it
 * is trivially testable (give it the current session and a chunk of time, get
 * the next session back).
 *
 * A sitting accumulates ACTIVE reading time — the same plausible words-over-ms
 * the pace estimator measures (see `pace.ts`) — so it never counts idle or
 * paused time. When the gap since the last read exceeds `SESSION_GAP_MS`, the
 * old sitting is done and a new one begins; the caller flushes the old one to
 * the server first (see `readingTime.svelte.ts`).
 */

import type { WorkKind } from './reading-schema';

/** A sitting: a client-owned id, its bounds (ms), and active seconds so far. */
export interface Session {
	/** The client's own id for this sitting — the server's upsert key. */
	clientId: string;
	startedAt: number;
	lastAt: number;
	seconds: number;
	/** What the reader opened the sitting on (context; a sitting may span works). */
	kind: WorkKind;
	slug: string;
	language: string;
}

export interface SessionCtx {
	kind: WorkKind;
	slug: string;
	language: string;
}

/** The wire shape the server's PUT /api/reading/sessions/ expects. Defined here
 *  (a store-free module) so both the store and the sync layer can import it
 *  without an import cycle. */
export interface SessionSync {
	client_id: string;
	started_at: number;
	last_seen_at: number;
	seconds: number;
	kind: WorkKind | '';
	book_slug: string;
	language: string;
}

/** A new sitting begins after this long with no reading. */
export const SESSION_GAP_MS = 30 * 60 * 1000;

/**
 * Fold `ms` of active reading (at wall-clock `now`) into `current`, starting a
 * fresh sitting when the gap since the last read exceeds `gapMs` (or there is no
 * current sitting). `rolled` tells the caller a NEW sitting began, so it can
 * flush the finished one before overwriting it.
 */
export function advanceSession(
	current: Session | null,
	ms: number,
	now: number,
	ctx: SessionCtx,
	newId: () => string,
	gapMs = SESSION_GAP_MS
): { session: Session; rolled: boolean } {
	const add = Math.max(0, Math.round(ms / 1000));
	const rolled = !current || now - current.lastAt > gapMs;
	const base: Session = rolled
		? { clientId: newId(), startedAt: now - Math.max(0, ms), lastAt: now, seconds: 0, ...ctx }
		: current;
	return {
		session: { ...base, seconds: base.seconds + add, lastAt: now },
		rolled
	};
}
