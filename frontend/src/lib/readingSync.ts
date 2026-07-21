import { browser } from '$app/environment';
import { apiFetch } from './api';
import {
	PROGRESS_KEY,
	MARKS_KEY,
	READING_DATA_KEYS,
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
interface ServerState {
	progress: ServerProgress[];
	marks: ServerMarks[];
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
					paragraph_index: rec.paragraph_index
				})
			}).catch(() => {});
		});
	}

	pushMarks(kind: WorkKind, slug: string, order: number, marks: Mark[], language: string) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`m:${workKey(kind, slug, order)}`, () => {
			apiFetch(`/api/reading/marks/${slug}/${order}/${this.#kindQuery(kind)}`, {
				method: 'PUT',
				body: JSON.stringify({ kind, language, marks })
			}).catch(() => {});
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
						...(Array.isArray(entry.m)
							? { marks: entry.m }
							: { highlights: legacy.h ?? [], notes: legacy.n ?? {} })
					};
				})
				.filter(Boolean)
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
		} catch {
			/* offline or API down — keep the local cache untouched */
		}
	}

	/**
	 * Sign-out teardown. Cancels any in-flight debounced pushes (they'd fire as
	 * unauthenticated 401s) and wipes the reader's own data from localStorage —
	 * on a shared device, anything left behind would be merged into the next
	 * account that signs in (`mergeOnSignIn`). Device preferences (theme, font,
	 * language) deliberately survive; they aren't identity data.
	 */
	clearOnSignOut() {
		if (!browser) return;
		for (const timer of this.#timers.values()) clearTimeout(timer);
		this.#timers.clear();
		for (const key of READING_DATA_KEYS) localStorage.removeItem(key);
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
		// Let open views know the cache changed underneath them.
		window.dispatchEvent(new CustomEvent('ochorus:sync'));
	}
}

export const readingSync = new ReadingSync();
