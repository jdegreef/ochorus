import { browser } from '$app/environment';
import { readingSync } from './readingSync';

/**
 * Highlights and notes, anchored at *paragraph* granularity (the index of a
 * top-level block within a chapter's `.reading` container). Paragraph-level is
 * robust — it survives re-rendering and font changes without the fragile
 * text-offset bookkeeping that character-range anchoring needs.
 *
 * Stored device-local in localStorage as the offline cache; when signed in each
 * change is mirrored to the account via `readingSync` (which owns the API call).
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
	#language = 'en';

	/** Load marks for a chapter into the reactive view. */
	load(slug: string, order: number, language = 'en') {
		this.#slug = slug;
		this.#order = order;
		this.#language = language;
		this.#hydrate();
	}

	/** (Re)read the current chapter's marks from the cache into the view. */
	#hydrate() {
		const entry = readAll()[chapterKey(this.#slug, this.#order)];
		this.highlights = new Set(entry?.h ?? []);
		this.notes = { ...(entry?.n ?? {}) };
	}

	/** Re-read after the cache was replaced underneath us (e.g. a sign-in sync). */
	refresh() {
		if (this.#slug) this.#hydrate();
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
		readingSync.pushMarks(this.#slug, this.#order, { h, n }, this.#language);
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
