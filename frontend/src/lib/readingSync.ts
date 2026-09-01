import { browser } from '$app/environment';
import { apiFetch } from './api';
import type { PlanState } from './planProgress.svelte';
import {
	PROGRESS_KEY,
	MARKS_KEY,
	FAVORITES_KEY,
	ACTIVITY_KEY,
	PLANS_KEY,
	LAST_SYNC_KEY,
	READING_DATA_KEYS,
	SIGN_OUT_DATA_KEYS,
	migrateLegacySermonState,
	workKey,
	workSlugKey,
	parseWorkKey,
	parseWorkSlugKey,
	type WorkKind,
	type Mark,
	type MarksStore,
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
interface ServerState {
	progress: ServerProgress[];
	marks: ServerMarks[];
	favorites?: ServerFavorite[];
	activity?: string[];
	plan_progress?: ServerPlanProgress[];
}


function readJson<T>(key: string, fallback: T): T {
	if (!browser) return fallback;
	try {
		return { ...fallback, ...JSON.parse(localStorage.getItem(key) || '{}') };
	} catch {
		return fallback;
	}
}

class ReadingSync {
	signedIn = false;
	#timers = new Map<string, ReturnType<typeof setTimeout>>();

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
	#debounce(key: string, fn: () => void, ms = 800) {
		clearTimeout(this.#timers.get(key));
		this.#timers.set(
			key,
			setTimeout(() => {
				this.#timers.delete(key);
				fn();
			}, ms)
		);
	}

	/** `?kind=` only for non-book works: book URLs stay byte-identical to the
	 * pre-#10 contract, so nothing changes for existing readers mid-deploy. */
	#kindQuery(kind: WorkKind): string {
		return kind === 'book' ? '' : `?kind=${kind}`;
	}

	pushProgress(kind: WorkKind, slug: string, rec: ProgressRecord) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`p:${workSlugKey(kind, slug)}`, () => {
			apiFetch(`/api/reading/progress/${slug}/${this.#kindQuery(kind)}`, {
				method: 'PUT',
				body: JSON.stringify({
					kind,
					language: rec.language,
					chapter_order: rec.order,
					paragraph_index: rec.paragraph_index,
					// The record's client-clock time, so the server keeps a newer
					// position when a stale tab flushes a late push (recency is judged
					// against the client's own clock — see reading/views _upsert_progress).
					updated_at: rec.at
				})
			})
				.then(() => this.#markSynced())
				.catch(() => {});
		});
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
			apiFetch(`/api/reading/marks/${slug}/${order}/${this.#kindQuery(kind)}`, {
				method: 'PUT',
				// `deleted` is always present (even when empty): it is the signal that
				// this client speaks the tombstone protocol, so the server unions
				// instead of blind-replacing. Older bundles omit it and keep replace.
				body: JSON.stringify({ kind, language, marks, deleted })
			})
				.then(() => this.#markSynced())
				.catch(() => {});
		});
	}

	/** Mirror a newly-recorded reading day to the account (append-only). */
	pushActivity(day: string) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`a:${day}`, () => {
			apiFetch(`/api/reading/activity/${day}/`, { method: 'PUT' })
				.then(() => this.#markSynced())
				.catch(() => {});
		});
	}

	/** Mirror a heart toggle (kind: author | book | plan | sermon). */
	pushFavorite(kind: string, slug: string, active: boolean) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`f:${kind}:${slug}`, () => {
			apiFetch(`/api/reading/favorites/${kind}/${slug}/`, {
				method: active ? 'PUT' : 'DELETE'
			})
				.then(() => this.#markSynced())
				.catch(() => {});
		});
	}

	/** Mirror a plan's progress (started + completed days) to the account. */
	pushPlan(slug: string, state: PlanState) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`plan:${slug}`, () => {
			apiFetch(`/api/reading/plan/${slug}/`, {
				method: 'PUT',
				body: JSON.stringify({ started_at: state.startedAt, done: state.done })
			})
				.then(() => this.#markSynced())
				.catch(() => {});
		});
	}

	/**
	 * First-sign-in reconciliation. Sends the local cache to the merge endpoint,
	 * then overwrites the cache with the merged server truth so both sides agree.
	 */
	async mergeOnSignIn() {
		if (!browser) return;
		// Fold any legacy sermon state in BEFORE building the payload: a merge
		// that read the cache pre-fold would upload without those marks, and
		// its response would then overwrite the folded cache — destroying
		// pre-upgrade sermon highlights.
		migrateLegacySermonState();
		const localProgress = readJson<ProgressMap>(PROGRESS_KEY, {});
		const localMarks = readJson<MarksStore>(MARKS_KEY, {});
		const localFavorites = readJson<Record<string, number>>(FAVORITES_KEY, {});
		const localPlans = readJson<Record<string, PlanState>>(PLANS_KEY, {});
		// Activity is a bare array, so read it directly (readJson spreads onto an
		// object fallback, which would mangle an array).
		let localActivity: string[] = [];
		try {
			const raw = JSON.parse(localStorage.getItem(ACTIVITY_KEY) || '[]');
			if (Array.isArray(raw)) localActivity = raw.filter((d) => typeof d === 'string');
		} catch {
			/* corrupt blob — treat as empty */
		}

		const payload = {
			progress: Object.entries(localProgress).map(([key, r]) => {
				const { kind, slug } = parseWorkSlugKey(key);
				return {
					kind,
					book_slug: slug,
					language: r.language || 'en',
					chapter_order: r.order,
					paragraph_index: r.paragraph_index || 0,
					updated_at: r.at
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
			favorites: Object.keys(localFavorites).map((key) => {
				const i = key.indexOf(':');
				return { kind: key.slice(0, i), slug: key.slice(i + 1) };
			}),
			activity: localActivity,
			plan_progress: Object.entries(localPlans).map(([slug, p]) => ({
				plan_slug: slug,
				started_at: p.startedAt,
				done: Array.isArray(p.done) ? p.done : []
			}))
		};

		try {
			const state = await apiFetch<ServerState>('/api/reading/merge/', {
				method: 'POST',
				body: JSON.stringify(payload)
			});
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
			this.#writeState(state);
			this.#markSynced();
		} catch {
			/* offline or API down — keep the local cache untouched */
		}
	}

	/**
	 * Sign-out teardown. Cancels any in-flight debounced pushes (they'd fire as
	 * unauthenticated 401s) and wipes the reader's *server-backed* data from
	 * localStorage — on a shared device, anything left behind would be merged
	 * into the next account that signs in (`mergeOnSignIn`).
	 *
	 * Uses SIGN_OUT_DATA_KEYS, NOT the full set: a store with no server copy
	 * (bookmarks) must not be destroyed by a routine sign-out/expiry, or the
	 * reader loses it for good. Those are cleared only by the explicit "clear
	 * reading data" control (`clearDeviceData`). Device preferences (theme, font,
	 * language) deliberately survive; they aren't identity data.
	 */
	clearOnSignOut() {
		this.#wipe(SIGN_OUT_DATA_KEYS);
	}

	/**
	 * Wipe ALL of the reader's own data from this device — the settings "clear
	 * reading data" control. Unlike the sign-out teardown this also clears stores
	 * with no server backup (bookmarks), because the reader asked to erase
	 * everything. Device preferences (theme, font, language) survive.
	 */
	clearDeviceData() {
		this.#wipe(READING_DATA_KEYS);
	}

	/** Cancel in-flight debounced pushes (they'd 401 after sign-out), remove the
	 * given keys, and tell open views the cache was emptied underneath them. */
	#wipe(keys: readonly string[]) {
		if (!browser) return;
		for (const timer of this.#timers.values()) clearTimeout(timer);
		this.#timers.clear();
		for (const key of keys) localStorage.removeItem(key);
		// Let open views (reader marks, continue-reading cards, plan pages) know
		// the cache was emptied underneath them.
		window.dispatchEvent(new CustomEvent('ochorus:sync'));
	}

	/** Overwrite the local cache with server state (used after a merge/pull). */
	#writeState(state: ServerState) {
		if (!browser) return;
		const progress: ProgressMap = {};
		for (const p of state.progress) {
			progress[workSlugKey(p.kind ?? 'book', p.book_slug)] = {
				order: p.chapter_order,
				paragraph_index: p.paragraph_index,
				language: p.language,
				at: Date.parse(p.updated_at) || Date.now()
			};
		}
		const marks: MarksStore = {};
		for (const m of state.marks) {
			marks[workKey(m.kind ?? 'book', m.book_slug, m.chapter_order)] = { m: m.marks ?? [] };
		}
		localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
		localStorage.setItem(MARKS_KEY, JSON.stringify(marks));
		if (state.favorites) {
			const favs: Record<string, number> = {};
			for (const f of state.favorites) {
				favs[`${f.kind}:${f.slug}`] = Date.parse(f.created_at) || Date.now();
			}
			localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs));
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
			localStorage.setItem(PLANS_KEY, JSON.stringify(plans));
		}
		// Let open views know the cache changed underneath them.
		window.dispatchEvent(new CustomEvent('ochorus:sync'));
	}
}

export const readingSync = new ReadingSync();
