import { browser } from '$app/environment';
import { JOURNAL_KEY } from './reading-schema';
import { readJSON, writeJSON } from './persisted';
import { readingSync } from './readingSync';
import { undo } from './undo.svelte';
import {
	cleanEntry,
	cleanStore,
	newEntryId,
	tombstone,
	type EntrySource,
	type JournalEntry,
	type JournalStore
} from './journal';

/**
 * The reactive journal — the Notebook's notes and prayers.
 *
 * localStorage is the offline source of truth, like every reading store; each
 * change mirrors to the account through `readingSync.pushJournal` (a PUT of the
 * whole entry, last-write-wins on `updatedAt`). A delete writes a tombstone
 * rather than dropping the row, so it syncs as a delete instead of an offline
 * device pushing the entry back.
 *
 * Every mutation re-reads the blob first: a second tab (a chapter open beside
 * the Notebook) may have written since this one hydrated.
 */

const readAll = (): JournalStore => cleanStore(readJSON<unknown>(JOURNAL_KEY, {}));

export type EntryDraft = Pick<JournalEntry, 'kind' | 'title' | 'body' | 'ref' | 'person' | 'group'>;

class Journal {
	/** Every entry, tombstones included — views filter through `visibleEntries`. */
	store = $state<JournalStore>({});

	constructor() {
		if (browser) {
			this.store = readAll();
			// A sign-in merge or another tab's write replaced the blob underneath us.
			window.addEventListener('ochorus:sync', () => (this.store = readAll()));
		}
	}

	/**
	 * Save one entry: re-read the blob (another tab may have written), put this
	 * entry in, write it back, and replace just this entry in memory — every
	 * other entry keeps its identity, so only its own card re-renders. Through
	 * the same cleaner as storage and sync, so every rule — a note carries no
	 * answer, person or reminder; a tombstone no text — holds in one place.
	 */
	#write(entry: JournalEntry, all: JournalStore = readAll()) {
		const e = cleanEntry(entry);
		if (!e) return;
		all[e.id] = e;
		writeJSON(JOURNAL_KEY, all);
		this.store[e.id] = e;
		readingSync.pushJournal(e);
	}

	/** Change a live entry (a prayer, when `prayerOnly`) from its stored state. */
	#mutate(id: string, change: (cur: JournalEntry) => JournalEntry, prayerOnly = false) {
		const all = readAll();
		const cur = all[id];
		if (!cur || cur.deleted || (prayerOnly && cur.kind !== 'prayer')) return;
		this.#write({ ...change(cur), updatedAt: Date.now() }, all);
	}

	/** A new entry; `source` when it was written from a passage in the reader. */
	add(draft: EntryDraft, source: EntrySource | null = null, now = Date.now()): void {
		this.#write({
			id: newEntryId(now),
			...draft,
			title: draft.title.trim(),
			body: draft.body.trim(),
			ref: draft.ref.trim(),
			person: draft.person.trim(),
			remind: '',
			updates: [],
			source,
			answer: '',
			answeredAt: null,
			createdAt: now,
			updatedAt: now
		});
	}

	update(id: string, patch: Partial<EntryDraft>) {
		const trimmed = Object.fromEntries(
			Object.entries(patch).map(([k, v]) => [k, typeof v === 'string' ? v.trim() : v])
		);
		this.#mutate(id, (cur) => ({ ...cur, ...trimmed }));
	}

	/** Add a dated follow-up to a prayer. */
	addUpdate(id: string, text: string, now = Date.now()) {
		if (!text.trim()) return;
		this.#mutate(id, (cur) => ({ ...cur, updates: [...cur.updates, { at: now, text: text.trim() }] }), true);
	}

	removeUpdate(id: string, at: number) {
		this.#mutate(id, (cur) => ({ ...cur, updates: cur.updates.filter((u) => u.at !== at) }), true);
	}

	/** Record the calendar reminder the reader added ('' clears it). */
	setRemind(id: string, remind: string) {
		this.#mutate(id, (cur) => ({ ...cur, remind }), true);
	}

	/** Mark a prayer answered (with how, if the reader says), or un-answer it. */
	setAnswered(id: string, answered: boolean, answer = '') {
		this.#mutate(
			id,
			(cur) => ({
				...cur,
				answeredAt: answered ? (cur.answeredAt ?? Date.now()) : null,
				answer: answered ? answer.trim() : ''
			}),
			true
		);
	}

	/** Delete, with a few seconds' Undo — a prayer journal is not a place to lose words. */
	remove(id: string) {
		const cur = this.store[id];
		if (!cur || cur.deleted) return;
		this.#mutate(id, (e) => tombstone(e));
		// The server keeps a tombstone sticky, so Undo re-creates the entry under a
		// fresh id rather than trying to revive the deleted one.
		undo.offer({
			restore: () => this.#write({ ...cur, id: newEntryId(), updatedAt: Date.now() })
		});
	}
}

export const journal = new Journal();
