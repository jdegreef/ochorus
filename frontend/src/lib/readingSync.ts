import { browser } from '$app/environment';
import { apiFetch } from './api';

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

const PROGRESS_KEY = 'ochorus:progress';
const MARKS_KEY = 'ochorus:marks';

export interface ProgressRecord {
	order: number;
	paragraph_index: number;
	language: string;
	at: number;
}
type ProgressMap = Record<string, ProgressRecord>;

interface StoredMark {
	id: string;
	p: number;
	s: number;
	e: number;
	note?: string;
}
interface ChapterEntry {
	m: StoredMark[];
}
type MarksMap = Record<string, ChapterEntry>;

interface ServerProgress {
	book_slug: string;
	language: string;
	chapter_order: number;
	paragraph_index: number;
	updated_at: string;
}
interface ServerMarks {
	book_slug: string;
	language: string;
	chapter_order: number;
	marks: StoredMark[];
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

// `slug:order` marks keys — slugs never contain ':' so split on the last one.
const marksKey = (slug: string, order: number) => `${slug}:${order}`;
function parseMarksKey(key: string): { slug: string; order: number } | null {
	const i = key.lastIndexOf(':');
	if (i < 0) return null;
	const order = Number(key.slice(i + 1));
	if (!Number.isFinite(order)) return null;
	return { slug: key.slice(0, i), order };
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

	pushProgress(slug: string, rec: ProgressRecord) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`p:${slug}`, () => {
			apiFetch(`/api/reading/progress/${slug}/`, {
				method: 'PUT',
				body: JSON.stringify({
					language: rec.language,
					chapter_order: rec.order,
					paragraph_index: rec.paragraph_index
				})
			}).catch(() => {});
		});
	}

	pushMarks(slug: string, order: number, marks: StoredMark[], language: string) {
		if (!this.signedIn || !browser) return;
		this.#debounce(`m:${slug}:${order}`, () => {
			apiFetch(`/api/reading/marks/${slug}/${order}/`, {
				method: 'PUT',
				body: JSON.stringify({ language, marks })
			}).catch(() => {});
		});
	}

	/**
	 * First-sign-in reconciliation. Sends the local cache to the merge endpoint,
	 * then overwrites the cache with the merged server truth so both sides agree.
	 */
	async mergeOnSignIn() {
		if (!browser) return;
		const localProgress = readJson<ProgressMap>(PROGRESS_KEY, {});
		const localMarks = readJson<MarksMap>(MARKS_KEY, {});

		const payload = {
			progress: Object.entries(localProgress).map(([slug, r]) => ({
				book_slug: slug,
				language: r.language || 'en',
				chapter_order: r.order,
				paragraph_index: r.paragraph_index || 0,
				updated_at: r.at
			})),
			marks: Object.entries(localMarks)
				.map(([key, entry]) => {
					const parsed = parseMarksKey(key);
					if (!parsed) return null;
					// A not-yet-migrated legacy entry ({h, n}) passes its legacy
					// keys through — the server converts, so nothing is lost.
					const legacy = entry as unknown as { h?: number[]; n?: Record<string, string> };
					return {
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
			this.#writeState(state);
		} catch {
			/* offline or API down — keep the local cache untouched */
		}
	}

	/** Overwrite the local cache with server state (used after a merge/pull). */
	#writeState(state: ServerState) {
		if (!browser) return;
		const progress: ProgressMap = {};
		for (const p of state.progress) {
			progress[p.book_slug] = {
				order: p.chapter_order,
				paragraph_index: p.paragraph_index,
				language: p.language,
				at: Date.parse(p.updated_at) || Date.now()
			};
		}
		const marks: MarksMap = {};
		for (const m of state.marks) {
			marks[marksKey(m.book_slug, m.chapter_order)] = { m: m.marks ?? [] };
		}
		localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
		localStorage.setItem(MARKS_KEY, JSON.stringify(marks));
		// Let open views know the cache changed underneath them.
		window.dispatchEvent(new CustomEvent('ochorus:sync'));
	}
}

export const readingSync = new ReadingSync();
