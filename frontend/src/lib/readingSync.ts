import { browser } from '$app/environment';
import { undo } from './undo.svelte';
import { apiFetch } from './api';
import { writeJSON } from './persisted';
import {
	mergeServerShelves,
	toServer as shelfToServer,
	type CustomShelf,
	type ServerShelf,
	type ShelvesStore
} from './shelvesData';
import { bookmarkTarget, clearPending, clearSent, pendingAt, pendingRemovals } from './removals';
import type { PlanState } from './planProgress.svelte';
import type { SessionSync } from './sessionClock';
import {
	cleanStore,
	fromServer,
	applyServerJournal,
	toServer,
	type JournalEntry,
	type JournalStore,
	type ServerJournalEntry
} from './journal';
import {
	PROGRESS_KEY,
	MARKS_KEY,
	FAVORITES_KEY,
	ACTIVITY_KEY,
	PLANS_KEY,
	BOOKMARKS_KEY,
	JOURNAL_KEY,
	SHELVES_KEY,
	JOURNAL_DIRTY_KEY,
	LAST_SYNC_KEY,
	READING_DATA_KEYS,
	SIGN_OUT_DATA_KEYS,
	SYNC_OWED_KEY,
	SYNC_STASH_KEY,
	migrateLegacySermonState,
	workKey,
	workSlugKey,
	parseWorkKey,
	parseWorkSlugKey,
	type WorkKind,
	type Mark,
	type MarksStore,
	type Bookmark,
	type BookmarksStore,
	type ProgressRecord,
	type ProgressMap
} from './reading-schema';

/**
 * Cross-device sync for reading progress, highlights and notes.
 *
 * localStorage is always the source of truth for the *offline* experience; this
 * module mirrors that cache to the Django API when the reader is signed in. To
 * avoid an import cycle (progress/marks → sync → progress/marks) it talks to
 * localStorage directly through the shared keys rather than importing those
 * stores. `auth` flips `signedIn` on session changes and calls `mergeOnSignIn()`
 * once, which reconciles whatever accumulated offline with the server and writes
 * the merged whole back over the local cache.
 */

interface ServerProgress {
	kind: WorkKind;
	book_slug: string;
	language: string;
	chapter_order: number;
	paragraph_index: number;
	updated_at: string;
	/** The writing device's own clock; null only from a client that sent none. */
	client_updated_at?: string | null;
	/** When the reader finished this work; null while in progress. */
	finished_at?: string | null;
}
interface ServerMarks {
	kind: WorkKind;
	book_slug: string;
	language: string;
	chapter_order: number;
	marks: Mark[];
	updated_at: string;
}
interface ServerFavorite {
	kind: string;
	slug: string;
	created_at: string;
}
interface ServerPlanProgress {
	plan_slug: string;
	started_at: string;
	done: number[];
	updated_at: string;
}
interface ServerBookmark {
	kind: WorkKind;
	book_slug: string;
	chapter_order: number;
	paragraph_index: number;
	bm_id: string;
	snippet: string;
	title: string;
}
interface ServerState {
	progress: ServerProgress[];
	marks: ServerMarks[];
	favorites?: ServerFavorite[];
	bookmarks?: ServerBookmark[];
	activity?: string[];
	plan_progress?: ServerPlanProgress[];
	/** The merge applied `removed` (an API with tombstones — see removals.ts). */
	removed_applied?: boolean;
	journal?: ServerJournalEntry[];
	/** Custom Bookshelf shelves, tombstones included (absent on an older API). */
	shelves?: ServerShelf[];
}

/**
 * The most journal the sign-in merge carries, in serialized characters.
 * Django rejects request bodies over 2.5MB (DATA_UPLOAD_MAX_MEMORY_SIZE) and
 * that would fail the WHOLE merge — progress, highlights, everything — so the
 * journal takes at most this share; what doesn't fit stays pending for the
 * next merge.
 */
const MERGE_JOURNAL_CHARS = 1_000_000;

/** A nullable server ISO datetime → epoch ms, or null (unset, or unparseable). */
function msOrNull(s?: string | null): number | null {
	return s ? Date.parse(s) || null : null;
}

function readJson<T>(key: string, fallback: T): T {
	if (!browser) return fallback;
	try {
		return { ...fallback, ...JSON.parse(localStorage.getItem(key) || '{}') };
	} catch {
		return fallback;
	}
}

/** Fired whenever the set of journal entries owed to the account changes, so
 *  the Notebook's sync indicator can re-read it (see journalSyncState). */
export const JOURNAL_PENDING_EVENT = 'ochorus:journal-pending';

class ReadingSync {
	signedIn = false;
	/** Pushes waiting on their debounce: the timer, and the push it will run —
	 *  kept so a sign-out can run it now instead. */
	#queue = new Map<string, { timer: ReturnType<typeof setTimeout>; fn: () => unknown }>();
	/** Pushes on the wire. A sign-out waits for these too: one that then fails
	 *  would record what it owed after the device was already wiped. */
	#inflight = new Set<Promise<unknown>>();
	/** The one merge in progress, shared by every caller (sign-in, settle, the
	 *  online listener) so the whole cache isn't uploaded twice at once. */
	#merging: Promise<void> | null = null;
	#flushing = false;

	constructor() {
		// Back online: deliver what was written while the connection was down,
		// instead of waiting for the next sign-in merge to carry it. A failed
		// push of anything else is recovered by a merge, which uploads the whole
		// cache (the account unions it).
		if (browser)
			window.addEventListener('online', () => {
				if (this.signedIn && this.#owed()) void this.mergeOnSignIn();
				else void this.flushJournal();
			});
	}

	/** Track a push until it settles. Every push goes through here. */
	#track(p: unknown) {
		if (!(p instanceof Promise)) return;
		this.#inflight.add(p);
		void p.finally(() => this.#inflight.delete(p));
	}

	/** A push failed: the device now holds changes the account doesn't. */
	#owe() {
		if (!this.#owed()) writeJSON(SYNC_OWED_KEY, Date.now());
	}

	#owed(): boolean {
		return browser && !!localStorage.getItem(SYNC_OWED_KEY);
	}

	/** Changes on this device the account doesn't have yet: a push queued or on
	 *  the wire, one that failed, journal entries owed, or removals whose DELETE
	 *  never landed. */
	hasUnsynced(): boolean {
		if (!browser) return false;
		return (
			this.#queue.size > 0 ||
			this.#inflight.size > 0 ||
			this.#owed() ||
			Object.keys(this.#pendingJournal()).length > 0 ||
			pendingRemovals().length > 0
		);
	}

	/**
	 * Get everything on this device to the account before the session ends:
	 * run the queued pushes now, wait for those already sent, and if anything is
	 * still owed, merge (which uploads the whole cache). Resolves true when the
	 * account has it all — false means signing out now would lose changes.
	 */
	async settle(): Promise<boolean> {
		if (!browser || !this.signedIn) return !this.hasUnsynced();
		for (const fn of this.#cancelAll()) this.#track(fn());
		await Promise.allSettled([...this.#inflight]);
		// Offline, a merge can only fail too — ask the reader straight away.
		if (this.hasUnsynced() && navigator.onLine !== false) await this.mergeOnSignIn();
		return !this.hasUnsynced();
	}

	/** Drop one queued push (a later write supersedes it). */
	#cancel(key: string) {
		clearTimeout(this.#queue.get(key)?.timer);
		this.#queue.delete(key);
	}

	/** Drop every queued push, handing back what they would have run. */
	#cancelAll(): (() => unknown)[] {
		const fns = [...this.#queue.values()].map((q) => {
			clearTimeout(q.timer);
			return q.fn;
		});
		this.#queue.clear();
		return fns;
	}

	setSignedIn(v: boolean) {
		this.signedIn = v;
	}

	/** Epoch-ms of the last successful sync, or null if never (read from storage
	 *  so the settings page needs no reactive bridge into this plain module). */
	readLastSynced(): number | null {
		if (!browser) return null;
		const v = Number(localStorage.getItem(LAST_SYNC_KEY));
		return Number.isFinite(v) && v > 0 ? v : null;
	}

	/** Record a successful sync. Kept quiet (no 'ochorus:sync' dispatch) so the
	 *  frequent debounced pushes don't churn every open view; the settings page
	 *  re-reads this on its own events. */
	#markSynced() {
		if (!browser) return;
		try {
			localStorage.setItem(LAST_SYNC_KEY, String(Date.now()));
		} catch {
			/* storage full / private mode — the timestamp just won't persist */
		}
	}

	/** Manual re-sync from the settings page: push the local cache and pull the
	 *  server truth (the same idempotent union merge used at sign-in). Resolves
	 *  false when there's no signed-in session to sync with. */
	async syncNow(): Promise<boolean> {
		if (!this.signedIn || !browser) return false;
		await this.mergeOnSignIn();
		return true;
	}

	/** Debounce a push, coalescing rapid updates to the same resource. */
	#debounce(key: string, fn: () => unknown, ms = 800) {
		this.#cancel(key);
		const timer = setTimeout(() => {
			this.#queue.delete(key);
			this.#track(fn());
		}, ms);
		this.#queue.set(key, { timer, fn });
	}

	/** `?kind=` only for non-book works: book URLs stay byte-identical to the
	 * pre-#10 contract, so nothing changes for existing readers mid-deploy. */
	#kindQuery(kind: WorkKind): string {
		return kind === 'book' ? '' : `?kind=${kind}`;
	}

	/** PUT one progress row. `extra` carries whatever rides on top of the shared
	 *  position body (a finished stamp, an unfinish signal); the position-body
	 *  contract lives here once so a live save and a finish can't drift. */
	#putProgress(kind: WorkKind, slug: string, rec: ProgressRecord, extra: object) {
		return apiFetch(`/api/reading/progress/${slug}/${this.#kindQuery(kind)}`, {
			method: 'PUT',
			body: JSON.stringify({
				kind,
				language: rec.language,
				chapter_order: rec.order,
				paragraph_index: rec.paragraph_index,
				// The record's client-clock time, so the server keeps a newer position
				// when a stale tab flushes a late push (recency is judged against the
				// client's own clock — see reading/views _upsert_progress).
				updated_at: rec.at,
				...extra
			})
		})
			.then(() => this.#markSynced())
			.catch(() => this.#owe());
	}

	pushProgress(kind: WorkKind, slug: string, rec: ProgressRecord) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`p:${workSlugKey(kind, slug)}`, () => {
			// Re-assert a finished stamp the record carries so the server keeps it
			// (it unions — the earliest wins, an omitted value never clears). A plain
			// position save of an unfinished work sends nothing extra.
			return this.#putProgress(kind, slug, rec, rec.finished_at ? { finished_at: rec.finished_at } : {});
		});
	}

	/**
	 * Mirror a finish / un-finish to the account IMMEDIATELY (not debounced).
	 * These are discrete actions, not high-frequency scroll saves, and going
	 * through the debounce would be a correctness hazard for the un-finish
	 * direction: a scroll save landing in the same window would coalesce the
	 * `unfinish` signal away, and the server's union would re-assert the finish.
	 * So this cancels any pending position push for the work (its position rides
	 * along here anyway) and PUTs straight away.
	 */
	setFinished(kind: WorkKind, slug: string, rec: ProgressRecord, finished: boolean) {
		if (!this.signedIn || !browser) return;
		const key = `p:${workSlugKey(kind, slug)}`;
		this.#cancel(key);
		// Finishing sends the stamp (server unions it); un-finishing sends the
		// explicit clear signal instead — the one thing that clears it.
		this.#track(
			this.#putProgress(kind, slug, rec, finished ? { finished_at: rec.finished_at } : { unfinish: true })
		);
	}

	/**
	 * The account's synced position in one work — what another device last
	 * pushed — or null when there is none, or we are offline or signed out.
	 * A read, so no debounce; `at` is the writing device's own clock (the
	 * server's when an old client sent none), comparable to a local record's.
	 */
	async fetchProgress(kind: WorkKind, slug: string): Promise<ProgressRecord | null> {
		if (!this.signedIn || !browser) return null;
		try {
			const r = await apiFetch<{
				chapter_order: number;
				paragraph_index: number;
				language: string;
				updated_at: string;
				client_updated_at: string | null;
				finished_at?: string | null;
			}>(`/api/reading/progress/${slug}/${this.#kindQuery(kind)}`);
			const at = Date.parse(r.client_updated_at ?? r.updated_at);
			if (!Number.isFinite(at)) return null;
			return {
				order: r.chapter_order,
				paragraph_index: r.paragraph_index,
				language: r.language,
				at,
				finished_at: msOrNull(r.finished_at)
			};
		} catch {
			return null;
		}
	}

	pushMarks(
		kind: WorkKind,
		slug: string,
		order: number,
		marks: Mark[],
		deleted: Record<string, number>,
		language: string
	) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`m:${workKey(kind, slug, order)}`, () => {
			return apiFetch(`/api/reading/marks/${slug}/${order}/${this.#kindQuery(kind)}`, {
				method: 'PUT',
				// `deleted` is always present (even when empty): it is the signal that
				// this client speaks the tombstone protocol, so the server unions
				// instead of blind-replacing. Older bundles omit it and keep replace.
				body: JSON.stringify({ kind, language, marks, deleted })
			})
				.then(() => this.#markSynced())
				.catch(() => this.#owe());
		});
	}

	/** Mirror a newly-recorded reading day to the account (append-only). */
	pushActivity(day: string) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`a:${day}`, () => {
			return apiFetch(`/api/reading/activity/${day}/`, { method: 'PUT' })
				.then(() => this.#markSynced())
				.catch(() => this.#owe());
		});
	}

	/** Mirror reading sittings (time on site) to the account. The server upserts
	 *  each by its client id with a union rule, so re-sending a growing sitting is
	 *  idempotent. Debounced per sitting so mid-read pushes coalesce. */
	pushSessions(sessions: SessionSync[]) {
		if (!this.signedIn || !browser || !sessions.length) return;
		this.#debounce(`s:${sessions[0].client_id}`, () => {
			return apiFetch('/api/reading/sessions/', {
				method: 'PUT',
				body: JSON.stringify({ sessions })
			})
				.then(() => this.#markSynced())
				.catch(() => this.#owe());
		});
	}

	/** Send sittings NOW — no debounce — from the tab-hide / unload path, where a
	 *  debounced timer would never fire. `keepalive` lets the PUT outlive the
	 *  page (and still carries the auth header, unlike sendBeacon). Without this
	 *  the final, unflushed seconds of every sitting were lost. */
	pushSessionsNow(sessions: SessionSync[]) {
		if (!this.signedIn || !browser || !sessions.length) return;
		this.#track(
			apiFetch('/api/reading/sessions/', {
				method: 'PUT',
				body: JSON.stringify({ sessions }),
				keepalive: true
			})
				.then(() => this.#markSynced())
				.catch(() => this.#owe())
		);
	}

	/** Mirror a heart toggle (kind: author | book | plan | sermon). */
	pushFavorite(kind: string, slug: string, active: boolean) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`f:${kind}:${slug}`, () => {
			// An un-heart carries this device's clock and, once the account has it,
			// clears its pending entry (see removals.ts); until then the next merge
			// carries it instead, so an offline un-heart isn't lost.
			const at = active ? null : pendingAt('favorite', kind, slug);
			const query = at ? `?at=${at}` : '';
			return apiFetch(`/api/reading/favorites/${kind}/${slug}/${query}`, {
				method: active ? 'PUT' : 'DELETE'
			})
				.then(() => {
					if (at) clearPending('favorite', kind, slug, at);
					this.#markSynced();
				})
				.catch(() => this.#owe());
		});
	}

	/**
	 * Remove a work from the reader's shelf on the account — the Bookshelf's
	 * "Remove from shelf". Not debounced (a discrete act), and it cancels any
	 * position push still queued for the work, which would otherwise land just
	 * after. The server keeps a tombstone so no device re-merges the position;
	 * `at` is the removal's pending entry, cleared on success (else the next
	 * merge carries it).
	 */
	removeProgress(kind: WorkKind, slug: string, at: number) {
		if (!this.signedIn || !browser) return;
		const key = `p:${workSlugKey(kind, slug)}`;
		this.#cancel(key);
		this.#track(apiFetch(`/api/reading/progress/${slug}/?kind=${kind}&at=${at}`, { method: 'DELETE' })
			.then(() => {
				clearPending('progress', kind, slug, at);
				this.#markSynced();
			})
			.catch(() => this.#owe()));
	}

	/** Mirror a saved bookmark to the account (a paragraph the reader saved). */
	pushBookmark(kind: WorkKind, slug: string, bm: Bookmark) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`bm:${workSlugKey(kind, slug)}:${bm.order}:${bm.p}`, () => {
			return apiFetch(`/api/reading/bookmarks/${kind}/${slug}/${bm.order}/${bm.p}/`, {
				method: 'PUT',
				body: JSON.stringify({ bm_id: bm.id, snippet: bm.snippet, title: bm.title })
			})
				.then(() => this.#markSynced())
				.catch(() => this.#owe());
		});
	}

	/** Mirror a removed bookmark to the account. */
	removeBookmark(kind: WorkKind, slug: string, order: number, p: number) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`bm:${workSlugKey(kind, slug)}:${order}:${p}`, () => {
			// Like an un-heart: carries this device's clock, and clears its pending
			// entry once the account has it (else the next merge carries it).
			const target = bookmarkTarget(slug, order, p);
			const at = pendingAt('bookmark', kind, target);
			const query = at ? `?at=${at}` : '';
			return apiFetch(`/api/reading/bookmarks/${kind}/${slug}/${order}/${p}/${query}`, {
				method: 'DELETE'
			})
				.then(() => {
					if (at) clearPending('bookmark', kind, target, at);
					this.#markSynced();
				})
				.catch(() => this.#owe());
		});
	}

	/** Journal entries the account hasn't confirmed: id → updatedAt written. */
	pendingJournal(): Record<string, number> {
		return this.#pendingJournal();
	}

	#pendingJournal(): Record<string, number> {
		return readJson<Record<string, number>>(JOURNAL_DIRTY_KEY, {});
	}

	#setPending(pending: Record<string, number>) {
		try {
			localStorage.setItem(JOURNAL_DIRTY_KEY, JSON.stringify(pending));
		} catch {
			/* storage full — the entry then just rides a later push again */
		}
		window.dispatchEvent(new CustomEvent(JOURNAL_PENDING_EVENT));
	}

	/** The account has these versions: stop owing them — unless the entry was
	 *  edited again since, in which case the newer version is still owed. */
	#confirmJournal(sent: JournalEntry[]) {
		const pending = this.#pendingJournal();
		for (const e of sent) if (pending[e.id] === e.updatedAt) delete pending[e.id];
		this.#setPending(pending);
	}

	/**
	 * Mirror a Notebook entry (a note or prayer, or its tombstone). The whole
	 * entry rides every PUT and the server keeps the newest by `updatedAt`, so
	 * debouncing per entry only coalesces keystroke-rapid saves. Every change is
	 * recorded as owed first — signed out, offline, or a failed PUT — so the
	 * sign-in merge carries exactly what the account is missing, not the whole
	 * journal.
	 */
	pushJournal(e: JournalEntry) {
		if (!browser) return;
		this.#setPending({ ...this.#pendingJournal(), [e.id]: e.updatedAt });
		if (!this.signedIn) return;
		this.#debounce(`j:${e.id}`, () => {
			return apiFetch(`/api/reading/journal/${e.id}/`, {
				method: 'PUT',
				body: JSON.stringify(toServer(e))
			})
				.then(() => {
					this.#confirmJournal([e]);
					this.#markSynced();
				})
				.catch(() => this.#owe());
		});
	}

	/**
	 * Deliver every journal entry the account is still owed, one PUT at a time,
	 * newest first — on reconnecting, after the sign-in merge (which carries at
	 * most ~1MB), and from the Notebook's "Sync now". Stops at the first failure:
	 * that is the connection gone again, and the rest wait for the next chance.
	 * Resolves whether everything owed was delivered.
	 */
	async flushJournal(): Promise<boolean> {
		if (!browser || !this.signedIn || this.#flushing) return false;
		this.#flushing = true;
		try {
			const pending = this.#pendingJournal();
			const store = cleanStore(readJson<JournalStore>(JOURNAL_KEY, {}));
			const owed = Object.values(store)
				.filter((e) => e.id in pending)
				.sort((a, b) => b.updatedAt - a.updatedAt);
			for (const e of owed) {
				try {
					await apiFetch(`/api/reading/journal/${e.id}/`, {
						method: 'PUT',
						body: JSON.stringify(toServer(e))
					});
				} catch {
					return false;
				}
				this.#confirmJournal([e]);
			}
			// Owed ids with no entry left on the device (cleared storage) can never
			// be delivered; stop counting them as waiting.
			const left = this.#pendingJournal();
			const onDevice = cleanStore(readJson<JournalStore>(JOURNAL_KEY, {}));
			for (const id of Object.keys(left)) if (!onDevice[id]) delete left[id];
			this.#setPending(left);
			if (owed.length) this.#markSynced();
			return true;
		} finally {
			this.#flushing = false;
		}
	}

	/**
	 * Mirror a custom shelf to the account — the whole shelf; the server merges
	 * its books per book (see shelvesData). Debounced per shelf, so a run of
	 * adds becomes one PUT carrying all of them. An offline or failed push is
	 * carried by the next merge, which sends every shelf.
	 */
	pushShelf(shelf: CustomShelf) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`sh:${shelf.id}`, () => {
			const latest = readJson<ShelvesStore>(SHELVES_KEY, {})[shelf.id] ?? shelf;
			return apiFetch(`/api/reading/shelves/${latest.id}/`, {
				method: 'PUT',
				body: JSON.stringify(shelfToServer(latest))
			})
				.then(() => this.#markSynced())
				.catch(() => this.#owe());
		});
	}

	/** Mirror a plan's progress (started + completed days) to the account. */
	pushPlan(slug: string, state: PlanState) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`plan:${slug}`, () => {
			return apiFetch(`/api/reading/plan/${slug}/`, {
				method: 'PUT',
				body: JSON.stringify({ started_at: state.startedAt, done: state.done })
			})
				.then(() => this.#markSynced())
				.catch(() => this.#owe());
		});
	}

	/**
	 * First-sign-in reconciliation. Sends the local cache to the merge endpoint,
	 * then overwrites the cache with the merged server truth so both sides agree.
	 */
	mergeOnSignIn(): Promise<void> {
		if (!browser) return Promise.resolve();
		return (this.#merging ??= this.#merge().finally(() => (this.#merging = null)));
	}

	async #merge() {
		// Only a failure from before this merge is settled by it: one that lands
		// while it is out may not be in its payload.
		const owedAtStart = localStorage.getItem(SYNC_OWED_KEY);
		// Fold any legacy sermon state in BEFORE building the payload: a merge
		// that read the cache pre-fold would upload without those marks, and
		// its response would then overwrite the folded cache — destroying
		// pre-upgrade sermon highlights.
		migrateLegacySermonState();
		const localProgress = readJson<ProgressMap>(PROGRESS_KEY, {});
		const localMarks = readJson<MarksStore>(MARKS_KEY, {});
		const localFavorites = readJson<Record<string, number>>(FAVORITES_KEY, {});
		const localBookmarks = readJson<BookmarksStore>(BOOKMARKS_KEY, {});
		const localPlans = readJson<Record<string, PlanState>>(PLANS_KEY, {});
		// Only what the account is owed, newest first, within the journal's share
		// of the request (see MERGE_JOURNAL_CHARS). Tombstones ride too: a delete
		// made offline must reach the account.
		const pending = this.#pendingJournal();
		const owed = Object.values(cleanStore(readJson<JournalStore>(JOURNAL_KEY, {})))
			.filter((e) => e.id in pending)
			.sort((a, b) => b.updatedAt - a.updatedAt);
		const journalRows: ServerJournalEntry[] = [];
		const journalSent: JournalEntry[] = [];
		let journalChars = 0;
		for (const e of owed) {
			const row = toServer(e);
			journalChars += JSON.stringify(row).length;
			if (journalChars > MERGE_JOURNAL_CHARS && journalRows.length) break;
			journalRows.push(row);
			journalSent.push(e);
		}
		// Activity is a bare array, so read it directly (readJson spreads onto an
		// object fallback, which would mangle an array).
		let localActivity: string[] = [];
		try {
			const raw = JSON.parse(localStorage.getItem(ACTIVITY_KEY) || '[]');
			if (Array.isArray(raw)) localActivity = raw.filter((d) => typeof d === 'string');
		} catch {
			/* corrupt blob — treat as empty */
		}

		const removed = pendingRemovals();
		const payload = {
			progress: Object.entries(localProgress).map(([key, r]) => {
				const { kind, slug } = parseWorkSlugKey(key);
				return {
					kind,
					book_slug: slug,
					language: r.language || 'en',
					chapter_order: r.order,
					paragraph_index: r.paragraph_index || 0,
					updated_at: r.at,
					// Carry a local finish up to the account (the merge unions it).
					...(r.finished_at ? { finished_at: r.finished_at } : {})
				};
			}),
			marks: Object.entries(localMarks)
				.map(([key, entry]) => {
					const parsed = parseWorkKey(key);
					if (!parsed) return null;
					// A not-yet-migrated legacy entry ({h, n}) passes its legacy
					// keys through — the server converts, so nothing is lost.
					const legacy = entry as unknown as { h?: number[]; n?: Record<string, string> };
					return {
						kind: parsed.kind,
						book_slug: parsed.slug,
						chapter_order: parsed.order,
						// Carry tombstones into the sign-in reconcile so a highlight
						// deleted offline stays deleted instead of the union resurrecting it.
						deleted: entry.d ?? {},
						...(Array.isArray(entry.m)
							? { marks: entry.m }
							: { highlights: legacy.h ?? [], notes: legacy.n ?? {} })
					};
				})
				.filter(Boolean),
			// Favorites are stored as "kind:slug" -> savedAt; kinds never contain ':'.
			// `saved_at` lets the server tell a heart re-saved after a removal
			// elsewhere (keep) from this device's stale copy of it (drop).
			favorites: Object.entries(localFavorites).map(([key, at]) => {
				const i = key.indexOf(':');
				return { kind: key.slice(0, i), slug: key.slice(i + 1), saved_at: at };
			}),
			// Removals whose live DELETE never landed (offline, a failed request).
			removed,
			// Bookmarks: a workSlugKey ("book:humility") -> that work's list. Flatten
			// to one row per saved paragraph; the server unions them by position.
			bookmarks: Object.entries(localBookmarks).flatMap(([key, list]) => {
				const { kind, slug } = parseWorkSlugKey(key);
				return (Array.isArray(list) ? list : []).map((b) => ({
					kind,
					book_slug: slug,
					chapter_order: b.order,
					paragraph_index: b.p,
					bm_id: b.id,
					snippet: b.snippet,
					title: b.title,
					// Lets the server tell a bookmark re-saved after a removal
					// elsewhere (keep) from this device's stale copy (drop).
					saved_at: b.at
				}));
			}),
			activity: localActivity,
			plan_progress: Object.entries(localPlans).map(([slug, p]) => ({
				plan_slug: slug,
				started_at: p.startedAt,
				done: Array.isArray(p.done) ? p.done : []
			})),
			journal: journalRows,
			// Every shelf, tombstones too: the server merges per book, so sending
			// what it already has is harmless, and this is how an offline change
			// (or a failed push) reaches it.
			shelves: Object.values(readJson<ShelvesStore>(SHELVES_KEY, {})).map(shelfToServer)
		};

		try {
			const state = await apiFetch<ServerState>('/api/reading/merge/', {
				method: 'POST',
				body: JSON.stringify(payload)
			});
			// Only an API that says it applied them: one from before tombstones
			// ignores `removed`, and clearing then would lose them.
			if (state.removed_applied) clearSent(removed);
			// Deploy-overlap guard: if we sent sermon rows but the server echoed
			// rows with no `kind` at all, it's the pre-#10 API — writing its
			// state back would re-key our sermon entries as books, making every
			// sermon highlight vanish locally with no self-heal. Keep the local
			// cache authoritative; the first merge after the API deploy syncs.
			const sentSermonRows =
				payload.progress.some((r) => r.kind !== 'book') ||
				payload.marks.some((r) => r !== null && r.kind !== 'book');
			const serverRows = [...state.progress, ...state.marks];
			const serverKnowsKinds = serverRows.some((r) => 'kind' in r);
			if (sentSermonRows && serverRows.length > 0 && !serverKnowsKinds) return;
			if (state.journal) this.#confirmJournal(journalSent);
			this.#writeState(state, {
				[PROGRESS_KEY]: localProgress,
				[MARKS_KEY]: localMarks,
				[FAVORITES_KEY]: localFavorites,
				[BOOKMARKS_KEY]: localBookmarks,
				[PLANS_KEY]: localPlans
			});
			// The account now holds everything this device sent.
			if (localStorage.getItem(SYNC_OWED_KEY) === owedAtStart) localStorage.removeItem(SYNC_OWED_KEY);
			this.#markSynced();
			// Whatever didn't fit the merge's share goes now, one entry at a time.
			if (state.journal) void this.flushJournal();
		} catch {
			/* offline or API down — keep the local cache untouched */
		}
	}

	/**
	 * Sign-out teardown. Cancels any in-flight debounced pushes (they'd fire as
	 * unauthenticated 401s) and wipes the reader's data from localStorage — on a
	 * shared device, anything left behind would be merged into the next account
	 * that signs in (`mergeOnSignIn`).
	 *
	 * Every reading store now has a server copy (bookmarks joined the synced set),
	 * so SIGN_OUT_DATA_KEYS clears them all — the reader's own copy is safe on the
	 * account. Device preferences (theme, font, language) deliberately survive;
	 * they aren't identity data.
	 */
	clearOnSignOut() {
		this.#wipe(SIGN_OUT_DATA_KEYS);
	}

	/**
	 * Wipe ALL of the reader's own data from this device — the settings "clear
	 * reading data" control: the sign-out set, plus any stash a session end set
	 * aside. Device preferences (theme, font, language) survive.
	 */
	clearDeviceData() {
		this.#wipe(READING_DATA_KEYS);
		if (browser) localStorage.removeItem(SYNC_STASH_KEY);
	}

	/**
	 * A session ended WITHOUT the reader choosing to — token expiry or
	 * revocation, a sign-out in another tab. Nobody can be asked, so anything
	 * the account doesn't have yet is set aside for that same account before the
	 * usual wipe (restoreStash puts it back at its next sign-in). It is never
	 * merged into anyone else's: a different account signing in discards it.
	 */
	endSession(email: string) {
		const data: Record<string, string> = {};
		if (browser && email && this.hasUnsynced()) {
			for (const key of SIGN_OUT_DATA_KEYS) {
				const v = localStorage.getItem(key);
				if (v !== null) data[key] = v;
			}
		}
		this.clearOnSignOut();
		// After the wipe, so the stash has the room the data had. writeJSON
		// warns the reader if even that fails.
		if (Object.keys(data).length) writeJSON(SYNC_STASH_KEY, { email, at: Date.now(), data });
	}

	/**
	 * At sign-in, before the merge: give a stash back to the account it was
	 * set aside for (onto an empty cache only — never over this session's own
	 * data), and drop it for anyone else or once it is a month old.
	 */
	restoreStash(email: string) {
		if (!browser) return;
		const stash = readJson<{ email?: string; at?: number; data?: Record<string, string> }>(
			SYNC_STASH_KEY,
			{}
		);
		localStorage.removeItem(SYNC_STASH_KEY);
		const fresh = Date.now() - (stash.at ?? 0) < 30 * 24 * 60 * 60 * 1000;
		if (!email || stash.email !== email || !fresh || !stash.data) return;
		for (const [key, value] of Object.entries(stash.data)) {
			if (localStorage.getItem(key) === null) localStorage.setItem(key, value);
		}
	}

	/** Cancel in-flight debounced pushes (they'd 401 after sign-out), remove the
	 * given keys, and tell open views the cache was emptied underneath them. */
	#wipe(keys: readonly string[]) {
		// A pending Undo must not resurrect what was just deliberately erased.
		undo.dismiss();
		if (!browser) return;
		this.#cancelAll();
		for (const key of keys) localStorage.removeItem(key);
		// Let open views (reader marks, continue-reading cards, plan pages) know
		// the cache was emptied underneath them.
		window.dispatchEvent(new CustomEvent('ochorus:sync'));
	}

	/**
	 * Server state for one keyed store, keeping what changed on this device
	 * while the merge was out: an entry that differs from what was sent (a
	 * highlight made, a heart toggled, a plan day ticked) keeps its local value,
	 * one removed since stays removed. That change's own push carries it up.
	 */
	#keepLocalEdits<T>(key: string, server: Record<string, T>, sent: Record<string, T>): Record<string, T> {
		const now = readJson<Record<string, T>>(key, {});
		if (JSON.stringify(now) === JSON.stringify(sent)) return server;
		const out = { ...server };
		for (const k of new Set([...Object.keys(now), ...Object.keys(sent)])) {
			if (JSON.stringify(now[k]) === JSON.stringify(sent[k])) continue;
			if (now[k] === undefined) delete out[k];
			else out[k] = now[k];
		}
		return out;
	}

	/** Overwrite the local cache with server state (used after a merge/pull),
	 *  keeping edits made while it was in flight (`sent` is each keyed store as
	 *  the merge sent it — see #keepLocalEdits). */
	#writeState(state: ServerState, sent: Record<string, Record<string, unknown>>) {
		if (!browser) return;
		const progress: ProgressMap = {};
		for (const p of state.progress) {
			progress[workSlugKey(p.kind ?? 'book', p.book_slug)] = {
				order: p.chapter_order,
				paragraph_index: p.paragraph_index,
				language: p.language,
				// The writing device's clock, like every other `at` — the server's
				// receive time is always later, and a local record stamped with it
				// would out-date every other device's genuine reading.
				at: Date.parse(p.client_updated_at ?? p.updated_at) || Date.now(),
				finished_at: msOrNull(p.finished_at)
			};
		}
		const marks: MarksStore = {};
		for (const m of state.marks) {
			marks[workKey(m.kind ?? 'book', m.book_slug, m.chapter_order)] = { m: m.marks ?? [] };
		}
		const keep = <T>(key: string, server: Record<string, T>) =>
			JSON.stringify(this.#keepLocalEdits(key, server, (sent[key] ?? {}) as Record<string, T>));
		localStorage.setItem(PROGRESS_KEY, keep(PROGRESS_KEY, progress));
		localStorage.setItem(MARKS_KEY, keep(MARKS_KEY, marks));
		// Shelves are MERGED into the device's copy, not replaced: an edit made
		// while the merge was in flight must survive, and an older API that
		// doesn't send `shelves` must not wipe them.
		if (Array.isArray(state.shelves)) {
			const local = readJson<ShelvesStore>(SHELVES_KEY, {});
			localStorage.setItem(SHELVES_KEY, JSON.stringify(mergeServerShelves(local, state.shelves)));
		}
		if (state.favorites) {
			const favs: Record<string, number> = {};
			for (const f of state.favorites) {
				favs[`${f.kind}:${f.slug}`] = Date.parse(f.created_at) || Date.now();
			}
			localStorage.setItem(FAVORITES_KEY, keep(FAVORITES_KEY, favs));
		}
		if (state.bookmarks) {
			// Regroup the flat server list back into workSlugKey -> Bookmark[], the
			// shape the bookmarks store reads. (The store re-hydrates on 'ochorus:sync'.)
			const store: BookmarksStore = {};
			for (const b of state.bookmarks) {
				const key = workSlugKey(b.kind ?? 'book', b.book_slug);
				const bm: Bookmark = {
					id: b.bm_id || `${b.chapter_order}:${b.paragraph_index}`,
					order: b.chapter_order,
					p: b.paragraph_index,
					snippet: b.snippet ?? '',
					title: b.title ?? '',
					// The save-time is a local-only field the server doesn't keep
					// (nothing reads it — the list sorts by position).
					at: Date.now()
				};
				(store[key] ??= []).push(bm);
			}
			localStorage.setItem(BOOKMARKS_KEY, keep(BOOKMARKS_KEY, store));
		}
		if (state.activity) {
			localStorage.setItem(
				ACTIVITY_KEY,
				JSON.stringify(state.activity.filter((d) => typeof d === 'string'))
			);
		}
		if (state.plan_progress) {
			const plans: Record<string, PlanState> = {};
			for (const p of state.plan_progress) {
				plans[p.plan_slug] = {
					startedAt: Date.parse(p.started_at) || Date.now(),
					done: Array.isArray(p.done) ? p.done : []
				};
			}
			localStorage.setItem(PLANS_KEY, keep(PLANS_KEY, plans));
		}
		if (state.journal) {
			const server: JournalStore = {};
			for (const j of state.journal) {
				const e = fromServer(j);
				if (e) server[e.id] = e;
			}
			// Applied over what's on disk NOW rather than overwriting it: an entry
			// typed while the request was in flight, or one that didn't fit this
			// merge, is still owed to the account and keeps its local version.
			const local = cleanStore(readJson<JournalStore>(JOURNAL_KEY, {}));
			localStorage.setItem(
				JOURNAL_KEY,
				JSON.stringify(applyServerJournal(server, local, this.#pendingJournal()))
			);
		}
		// Let open views know the cache changed underneath them.
		window.dispatchEvent(new CustomEvent('ochorus:sync'));
	}
}

export const readingSync = new ReadingSync();
