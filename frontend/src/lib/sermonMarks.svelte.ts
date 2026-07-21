import { browser } from '$app/environment';
import { readingSync } from './readingSync';
import { readJSON, writeJSON } from './persisted';
import { SERMON_MARKS_KEY as KEY, DEFAULT_HIGHLIGHT } from './reading-schema';
import type { Mark, Segment } from './marks.svelte';

/**
 * Text-range highlights and notes for **sermons**.
 *
 * A sermon is a single body (no chapters), so — unlike book marks
 * (`marks.svelte.ts`, keyed by `slug:order` and mirrored to the account) —
 * these are keyed by sermon slug alone and kept device-local in localStorage.
 * The range model (`{ id, p, s, e, note? }`) and the DOM plumbing
 * (`rangeMarks.ts`) are shared with the book reader; only the persistence
 * keying differs. Account sync can come later without changing this shape.
 */

type Store = Record<string, Mark[]>; // sermon slug -> its marks

const readAll = (): Store => readJSON<Store>(KEY, {});
const writeAll = (store: Store) => writeJSON(KEY, store);

const rangeKey = (m: Segment) => `${m.p}:${m.s}:${m.e}`;

class SermonMarks {
	/** Reactive marks of the currently open sermon, sorted by position. */
	list = $state<Mark[]>([]);
	#slug = '';
	#language = 'en';

	constructor() {
		// The cache can be replaced underneath us (sign-in merge / sign-out wipe) —
		// re-derive open sermon views when that happens.
		if (browser) window.addEventListener('ochorus:sync', () => this.refresh());
	}

	load(slug: string, language = 'en') {
		this.#slug = slug;
		this.#language = language;
		this.#hydrate();
	}

	#hydrate() {
		this.list = [...(readAll()[this.#slug] ?? [])].sort((a, b) => a.p - b.p || a.s - b.s);
	}

	/** Re-read after the cache was replaced underneath us. */
	refresh() {
		if (this.#slug) this.#hydrate();
	}

	#persist() {
		const store = readAll();
		if (this.list.length === 0) delete store[this.#slug];
		else store[this.#slug] = this.list;
		writeAll(store);
		readingSync.pushSermonMarks(this.#slug, this.list, this.#language);
	}

	/** Add a group of range segments (one selection) as a single mark unit. */
	add(segments: Segment[], note?: string, color?: string): string {
		const first = segments[0];
		if (!first) return '';
		const id = `${Date.now().toString(36)}:${first.p}:${first.s}`;
		const tint = color && color !== DEFAULT_HIGHLIGHT ? { color } : {};
		const existing = new Set(this.list.map(rangeKey));
		const fresh = segments
			.filter((seg) => !existing.has(rangeKey(seg)))
			.map((seg, i) => ({ id, ...seg, ...tint, ...(i === 0 && note ? { note } : {}) }));
		this.list = [...this.list, ...fresh].sort((a, b) => a.p - b.p || a.s - b.s);
		this.#persist();
		return id;
	}

	/** The highlight colour of a mark group (default gold when unset). */
	getColor(id: string): string {
		return this.list.find((m) => m.id === id)?.color ?? DEFAULT_HIGHLIGHT;
	}

	/** Recolour every segment of a mark group (default clears the stored key). */
	setColor(id: string, color: string) {
		this.list = this.list.map((m) => {
			if (m.id !== id) return m;
			const { color: _drop, ...rest } = m;
			return color && color !== DEFAULT_HIGHLIGHT ? { ...rest, color } : rest;
		});
		this.#persist();
	}

	/** Remove every segment of a mark group. */
	remove(id: string) {
		this.list = this.list.filter((m) => m.id !== id);
		this.#persist();
	}

	/** The group id whose segments already cover this exact selection, if any. */
	groupCovering(segments: Segment[]): string | null {
		if (!segments.length) return null;
		const byKey = new Map(this.list.map((m) => [rangeKey(m), m]));
		if (!segments.every((s) => byKey.has(rangeKey(s)))) return null;
		return byKey.get(rangeKey(segments[0]))?.id ?? null;
	}

	getNote(id: string): string {
		return this.list.find((m) => m.id === id && m.note)?.note ?? '';
	}

	setNote(id: string, text: string) {
		const trimmed = text.trim();
		let placed = false;
		this.list = this.list.map((m) => {
			if (m.id !== id) return m;
			const { note: _drop, ...rest } = m;
			if (!placed && trimmed) {
				placed = true;
				return { ...rest, note: trimmed }; // note lives on the first segment
			}
			return rest;
		});
		this.#persist();
	}

	/** Every sermon's marks, for the notebook. */
	all(): { slug: string; marks: Mark[] }[] {
		return Object.entries(readAll())
			.filter(([, ms]) => ms?.length)
			.map(([slug, marks]) => ({ slug, marks }));
	}
}

export const sermonMarks = new SermonMarks();
