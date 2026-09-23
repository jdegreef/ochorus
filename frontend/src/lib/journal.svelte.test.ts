import { beforeEach, describe, expect, it } from 'vitest';
import { journal } from './journal.svelte';
import { undo } from './undo.svelte';
import { JOURNAL_DIRTY_KEY, JOURNAL_KEY } from './reading-schema';

const stored = () => JSON.parse(localStorage.getItem(JOURNAL_KEY) || '{}');
const owed = () => JSON.parse(localStorage.getItem(JOURNAL_DIRTY_KEY) || '{}');
const draft = { title: '', body: 'For Anna', ref: '', person: 'Anna', group: 'family' as const, collection: '' };
const only = () => Object.values(journal.store).filter((e) => !e.deleted);

beforeEach(() => {
	localStorage.clear();
	journal.store = {};
	undo.dismiss();
});

describe('journal store', () => {
	it('adds an entry to storage and memory, and owes it to the account', () => {
		journal.add({ ...draft, kind: 'prayer' });
		const [e] = only();
		expect(e).toMatchObject({ kind: 'prayer', body: 'For Anna', person: 'Anna', group: 'family' });
		expect(stored()[e.id].body).toBe('For Anna');
		// Signed out: nothing is pushed, so the entry waits for the sign-in merge.
		expect(owed()[e.id]).toBe(e.updatedAt);
	});

	it('keeps prayer things off a note', () => {
		journal.add({ ...draft, kind: 'note' });
		const [e] = only();
		expect(e).toMatchObject({ person: '', group: '' });
		journal.setAnswered(e.id, true, 'yes');
		journal.addUpdate(e.id, 'news');
		expect(journal.store[e.id]).toMatchObject({ answeredAt: null, updates: [] });
	});

	it('answers, un-answers and follows up a prayer', () => {
		journal.add({ ...draft, kind: 'prayer' });
		const id = only()[0].id;
		journal.addUpdate(id, '  Interview Friday  ');
		journal.setAnswered(id, true, ' She got it ');
		expect(journal.store[id]).toMatchObject({ answer: 'She got it' });
		expect(journal.store[id].updates.map((u) => u.text)).toEqual(['Interview Friday']);
		journal.setAnswered(id, false);
		expect(journal.store[id]).toMatchObject({ answeredAt: null, answer: '' });
	});

	it('deletes to a tombstone with no words, and Undo brings it back under a new id', () => {
		journal.add({ ...draft, kind: 'prayer' });
		const id = only()[0].id;
		journal.remove(id);
		expect(stored()[id]).toMatchObject({ deleted: true, body: '', person: '' });
		expect(only()).toHaveLength(0);
		undo.act();
		const back = only();
		expect(back).toHaveLength(1);
		expect(back[0].id).not.toBe(id);
		expect(back[0].body).toBe('For Anna');
	});

	it('replaces only the changed entry in memory', () => {
		journal.add({ ...draft, kind: 'prayer', body: 'one' });
		journal.add({ ...draft, kind: 'prayer', body: 'two' });
		const [a, b] = Object.keys(journal.store);
		const before = journal.store[b];
		journal.update(a, { body: 'one, edited' });
		expect(journal.store[a].body).toBe('one, edited');
		expect(journal.store[b]).toBe(before);
	});

	it('renames a collection across its entries, and takes it apart keeping them', () => {
		journal.add({ ...draft, kind: 'note', body: 'one', collection: 'Romans' });
		journal.add({ ...draft, kind: 'note', body: 'two', collection: 'romans' });
		journal.add({ ...draft, kind: 'note', body: 'three', collection: 'Other' });
		journal.renameCollection('ROMANS', 'Romans study');
		const names = () => only().map((e) => e.collection).sort();
		expect(names()).toEqual(['Other', 'Romans study', 'Romans study']);
		journal.renameCollection('Romans study', '');
		expect(names()).toEqual(['', '', 'Other']);
		expect(only()).toHaveLength(3);
	});

	it('pins an entry, and takes the pin out', () => {
		journal.add({ ...draft, kind: 'note', body: 'Be still' });
		const id = only()[0].id;
		journal.setPinned(id, true);
		expect(journal.store[id].pinnedAt).toBeGreaterThan(0);
		expect(stored()[id].pinnedAt).toBe(journal.store[id].pinnedAt);
		journal.setPinned(id, false);
		expect(journal.store[id].pinnedAt).toBeNull();
	});
});
