import { readingSync } from './readingSync';
import { readJSON, writeJSON } from './persisted';
import {
	MARKS_KEY,
	migrateLegacySermonState,
	workKey,
	parseWorkKey,
	type WorkKind,
	type MarksStore,
	type Mark
} from './reading-schema';

/**
 * Text-range highlights and notes.
 *
 * A mark is a character range inside one paragraph of a chapter:
 *   { id, p, s, e, note? }
 * `p` is the top-level block index in the `.reading` container; `s`/`e` index
 * that paragraph's *text content* — layout-independent, so ranges survive
 * font-size and measure changes. `e === -1` means "to the paragraph's end"
 * (migrated legacy whole-paragraph marks). A selection spanning paragraphs is
 * one mark per paragraph sharing an `id`, toggling/annotating as a unit.
 *
 * Stored device-local in localStorage as the offline cache; when signed in
 * each change mirrors to the account via `readingSync`. Legacy paragraph-level
 * entries ({h, n}) are migrated to ranges on first read.
 */

// Re-exported so components already importing `Mark` from this store keep working.
export type { Mark };

interface LegacyEntry {
	h?: number[];
	n?: Record<number, string>;
}

function fromLegacy(entry: LegacyEntry): Mark[] {
	const byP = new Map<number, Mark>();
	for (const p of entry.h ?? []) {
		byP.set(p, { id: `legacy:${p}`, p, s: 0, e: -1 });
	}
	for (const [k, v] of Object.entries(entry.n ?? {})) {
		const p = Number(k);
		if (!Number.isFinite(p) || !v?.trim()) continue;
		const mark = byP.get(p) ?? { id: `legacy:${p}`, p, s: 0, e: -1 };
		mark.note = v.trim();
		byP.set(p, mark);
	}
	return [...byP.values()].sort((a, b) => a.p - b.p);
}

/** Read the store, migrating any legacy entries in place. */
function readAll(): MarksStore {
	migrateLegacySermonState();
	const raw = readJSON<MarksStore>(MARKS_KEY, {});
	let migrated = false;
	for (const [key, entry] of Object.entries(raw)) {
		if (entry && !Array.isArray(entry.m) && ('h' in entry || 'n' in entry)) {
			raw[key] = { m: fromLegacy(entry as unknown as LegacyEntry) };
			migrated = true;
		}
	}
	if (migrated) writeJSON(MARKS_KEY, raw);
	return raw;
}

const writeAll = (store: MarksStore) => writeJSON(MARKS_KEY, store);

export interface Segment {
	p: number;
	s: number;
	e: number;
}

const rangeKey = (m: Segment) => `${m.p}:${m.s}:${m.e}`;

class Marks {
	/** Reactive marks of the currently open chapter, sorted by position. */
	list = $state<Mark[]>([]);
	#slug = '';
	#order = 0;
	#language = 'en';
	#kind: WorkKind = 'book';

	load(slug: string, order: number, language = 'en', kind: WorkKind = 'book') {
		this.#slug = slug;
		this.#order = order;
		this.#language = language;
		this.#kind = kind;
		this.#hydrate();
	}

	#hydrate() {
		const entry = readAll()[workKey(this.#kind, this.#slug, this.#order)];
		this.list = [...(entry?.m ?? [])].sort((a, b) => a.p - b.p || a.s - b.s);
	}

	/** Re-read after the cache was replaced underneath us (e.g. sign-in sync). */
	refresh() {
		if (this.#slug) this.#hydrate();
	}

	#persist() {
		const store = readAll();
		const key = workKey(this.#kind, this.#slug, this.#order);
		if (this.list.length === 0) delete store[key];
		else store[key] = { m: this.list };
		writeAll(store);
		readingSync.pushMarks(this.#kind, this.#slug, this.#order, this.list, this.#language);
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

	/** Mark-group count for a chapter without loading it (for the TOC). */
	countFor(slug: string, order: number, kind: WorkKind = 'book'): number {
		const e = readAll()[workKey(kind, slug, order)];
		if (!e?.m) return 0;
		return new Set(e.m.map((m) => m.id)).size;
	}

	/** Every work's marks across books and sermons, for the notebook. */
	all(): { kind: WorkKind; slug: string; order: number; marks: Mark[] }[] {
		const out: { kind: WorkKind; slug: string; order: number; marks: Mark[] }[] = [];
		for (const [key, entry] of Object.entries(readAll())) {
			const parsed = parseWorkKey(key);
			if (parsed && entry.m?.length) {
				out.push({ ...parsed, marks: entry.m });
			}
		}
		return out;
	}
}

export const marks = new Marks();
