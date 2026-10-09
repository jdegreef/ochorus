import { readJSON } from './persisted';
import { MARKS_KEY, parseWorkKey, type MarksStore, type WorkKind } from './reading-schema';

export interface DailyHighlight {
	kind: WorkKind;
	slug: string;
	order: number;
	/** The passage as it was highlighted (the mark's stored quote, ≤200 chars). */
	text: string;
	note?: string;
}

/** Shorter than this is a word or two picked out, not a passage to return to. */
const MIN_CHARS = 40;

/**
 * One of the reader's own highlights, a different one each day: the passages
 * they marked are worth meeting again, and the dashboard is where they come
 * back. Chosen from what is on this device (the marks store the sign-in sync
 * keeps whole) — only marks that carry their quote (`q`, stored since marks
 * learned to re-anchor themselves) and are long enough to read as a passage.
 * A multi-paragraph highlight is one group: its first segment stands for it.
 * Deterministic for a day (`day` is a local day number), stable however the
 * store's keys happen to be ordered. Null when there is nothing to show.
 */
export function dailyHighlight(day: number, store: MarksStore = readJSON<MarksStore>(MARKS_KEY, {})): DailyHighlight | null {
	const seen = new Set<string>();
	const pool: (DailyHighlight & { id: string })[] = [];
	for (const [key, chapter] of Object.entries(store)) {
		const where = parseWorkKey(key);
		if (!where) continue;
		for (const m of chapter?.m ?? []) {
			if (seen.has(m.id)) continue;
			seen.add(m.id);
			const text = m.q?.trim();
			if (!text || text.length < MIN_CHARS) continue;
			pool.push({ ...where, text, note: m.note || undefined, id: m.id });
		}
	}
	if (!pool.length) return null;
	pool.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
	const { id: _id, ...pick } = pool[((day % pool.length) + pool.length) % pool.length];
	return pick;
}
