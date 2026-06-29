import { browser } from '$app/environment';

/**
 * Highlights and notes, anchored at *paragraph* granularity (the index of a
 * top-level block within a chapter's `.reading` container). Paragraph-level is
 * robust — it survives re-rendering and font changes without the fragile
 * text-offset bookkeeping that character-range anchoring needs.
 *
 * Stored device-local in localStorage now; syncs to the account when login
 * lands (the shape mirrors what a future `/api/reading/marks` would return).
 */

const KEY = 'ochorus:marks';

interface ChapterMarks {
	h: number[]; // highlighted paragraph indices
	n: Record<number, string>; // paragraph index -> note text
}

type Store = Record<string, ChapterMarks>;

const chapterKey = (slug: string, order: number) => `${slug}:${order}`;

function readAll(): Store {
	if (!browser) return {};
	try {
		return JSON.parse(localStorage.getItem(KEY) || '{}');
	} catch {
		return {};
	}
}

function writeAll(store: Store) {
	if (browser) localStorage.setItem(KEY, JSON.stringify(store));
}

class Marks {
	// Reactive view of the *currently open* chapter.
	highlights = $state<Set<number>>(new Set());
	notes = $state<Record<number, string>>({});
	#slug = '';
	#order = 0;

	/** Load marks for a chapter into the reactive view. */
	load(slug: string, order: number) {
		this.#slug = slug;
		this.#order = order;
		const entry = readAll()[chapterKey(slug, order)];
		this.highlights = new Set(entry?.h ?? []);
		this.notes = { ...(entry?.n ?? {}) };
	}

	#persist() {
		const store = readAll();
		const key = chapterKey(this.#slug, this.#order);
		const h = [...this.highlights].sort((a, b) => a - b);
		const n = this.notes;
		if (h.length === 0 && Object.keys(n).length === 0) {
			delete store[key];
		} else {
			store[key] = { h, n };
		}
		writeAll(store);
	}

	isHighlighted(i: number) {
		return this.highlights.has(i);
	}

	toggleHighlight(i: number) {
		const next = new Set(this.highlights);
		if (next.has(i)) next.delete(i);
		else next.add(i);
		this.highlights = next;
		this.#persist();
	}

	getNote(i: number): string {
		return this.notes[i] ?? '';
	}

	setNote(i: number, text: string) {
		const next = { ...this.notes };
		const trimmed = text.trim();
		if (trimmed) next[i] = trimmed;
		else delete next[i];
		this.notes = next;
		this.#persist();
	}

	/** Count of marks in a chapter without loading it (for the contents page). */
	countFor(slug: string, order: number): number {
		const e = readAll()[chapterKey(slug, order)];
		if (!e) return 0;
		return e.h.length + Object.keys(e.n).length;
	}
}

export const marks = new Marks();
