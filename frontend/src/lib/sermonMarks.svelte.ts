import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { SERMON_MARKS_KEY as KEY } from './reading-schema';
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

	constructor() {
		// The cache can be replaced underneath us (sign-out wipe) — re-derive.
		if (browser) window.addEventListener('ochorus:sync', () => this.refresh());
	}

	load(slug: string) {
		this.#slug = slug;
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
	}

	/** Add a group of range segments (one selection) as a single mark unit. */
	add(segments: Segment[], note?: string): string {
		const first = segments[0];
		if (!first) return '';
		const id = `${Date.now().toString(36)}:${first.p}:${first.s}`;
		const existing = new Set(this.list.map(rangeKey));
		const fresh = segments
			.filter((seg) => !existing.has(rangeKey(seg)))
			.map((seg, i) => ({ id, ...seg, ...(i === 0 && note ? { note } : {}) }));
		this.list = [...this.list, ...fresh].sort((a, b) => a.p - b.p || a.s - b.s);
		this.#persist();
		return id;
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
