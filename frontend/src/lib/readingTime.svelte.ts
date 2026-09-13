import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { SESSION_KEY } from './reading-schema';
import { readingSync } from './readingSync';
import { advanceSession, type Session, type SessionCtx } from './sessionClock';

/**
 * "Time on site": how long the reader actually spends reading.
 *
 * Fed by the chapter reader from the SAME plausible words-over-ms signal the
 * pace estimator consumes (`readingPace.record` is called right beside
 * `readingTime.record`), so this counts real, foreground, non-idle reading —
 * never a tab left open. It accumulates that time into the current *sitting*
 * (see `sessionClock.ts`), buffers it in localStorage, and syncs the sitting to
 * the account (throttled, and flushed when the tab is hidden or closed). The
 * server upserts by the sitting's client id with a union rule, so a retry or a
 * second device never double-counts.
 *
 * Signed-out reading still accumulates locally; the push is a no-op until sign
 * in, after which the next `record` (or a hide/unload flush) sends the buffered
 * sitting. Device-scoped and wiped on sign-out like the rest of the reader's
 * data (SESSION_KEY is in READING_DATA_KEYS).
 */

// Don't spam the API mid-sitting: push accumulated time at most this often.
const PUSH_EVERY_MS = 30 * 1000;

function newId(): string {
	const c = globalThis.crypto;
	if (c && 'randomUUID' in c) return c.randomUUID();
	return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

class ReadingTime {
	#session: Session | null = null;
	#lastPush = 0;

	constructor() {
		if (!browser) return;
		this.#session = readJSON<Session | null>(SESSION_KEY, null);
		// Flush the sitting when the reader leaves — a hidden tab or a close is
		// exactly where the last, unpushed seconds would otherwise be lost. Use
		// the immediate (keepalive) path: a debounced push never fires on unload.
		document.addEventListener('visibilitychange', () => {
			if (document.visibilityState === 'hidden') this.flush(true);
		});
		window.addEventListener('pagehide', () => this.flush(true));
	}

	/**
	 * Record a chunk of active reading (`ms`), with what's being read. Called
	 * beside `readingPace.record` from the chapter reader, so `ms` is already the
	 * bounded, plausible reading time the pace estimator validated.
	 */
	record(ms: number, ctx: SessionCtx): void {
		if (!browser || !(ms > 0)) return;
		const now = Date.now();
		const { session, rolled } = advanceSession(this.#session, ms, now, ctx, newId);
		// A new sitting began — send the finished one before overwriting it. (When
		// signed out this push no-ops, so only the CURRENT sitting is retained for
		// the post-sign-in flush; earlier signed-out sittings aren't queued. Time
		// on site is a signed-in metric, so this is an accepted edge, not a gap.)
		if (rolled && this.#session) this.#push(this.#session);
		this.#session = session;
		writeJSON(SESSION_KEY, session);
		if (now - this.#lastPush > PUSH_EVERY_MS) this.flush();
	}

	/**
	 * Send the current sitting to the server. `immediate` (the tab-hide / unload
	 * path) sends synchronously with keepalive so it isn't lost to a torn-down
	 * event loop; the default (mid-read) path debounces so bursts coalesce.
	 */
	flush(immediate = false): void {
		if (this.#session && this.#session.seconds > 0) this.#push(this.#session, immediate);
	}

	#push(s: Session, immediate = false): void {
		this.#lastPush = Date.now();
		const rows = [
			{
				client_id: s.clientId,
				started_at: s.startedAt,
				last_seen_at: s.lastAt,
				seconds: s.seconds,
				kind: s.kind,
				book_slug: s.slug,
				language: s.language
			}
		];
		if (immediate) readingSync.pushSessionsNow(rows);
		else readingSync.pushSessions(rows);
	}
}

/** The reading-time tracker. Named `readingTimer` (not `readingTime`) to avoid
 *  colliding with the "N min read" formatter of the same idea in `reading.ts`. */
export const readingTimer = new ReadingTime();
