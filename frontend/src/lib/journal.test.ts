import { describe, it, expect } from 'vitest';
import {
	cleanEntry,
	cleanSource,
	composeDaily,
	dailyStreak,
	dailyVerse,
	cleanStore,
	formatRemind,
	fromServer,
	toServer,
	knownPeople,
	parseRemind,
	prayersByPerson,
	daysWaited,
	groupByDay,
	journalStats,
	applyServerJournal,
	newEntryId,
	tombstone,
	visibleEntries,
	type JournalEntry
} from './journal';

const DAY = 86_400_000;
const T0 = Date.UTC(2026, 8, 1, 12);

function entry(id: string, over: Partial<JournalEntry> = {}): JournalEntry {
	return {
		id,
		kind: 'note',
		title: '',
		body: id,
		ref: '',
		person: '',
		group: '',
		remind: '',
		updates: [],
		source: null,
		answer: '',
		answeredAt: null,
		createdAt: T0,
		updatedAt: T0,
		...over
	};
}

describe('journal entries', () => {
	it('mints ids the server accepts', () => {
		expect(newEntryId(T0, () => 0.5)).toMatch(/^[A-Za-z0-9_-]{1,64}$/);
		expect(newEntryId(T0, () => 0.1)).not.toBe(newEntryId(T0, () => 0.2));
	});

	it('drops corrupt rows and never lets a note carry an answer', () => {
		const store = cleanStore({
			a: entry('a'),
			bad: { id: 'bad id', kind: 'note' },
			poem: { ...entry('poem'), kind: 'poem' },
			n: entry('n', { answeredAt: T0, answer: 'x' })
		});
		expect(Object.keys(store).sort()).toEqual(['a', 'n']);
		expect(store.n.answeredAt).toBeNull();
		expect(store.n.answer).toBe('');
		expect(cleanStore([1, 2])).toEqual({});
		expect(cleanEntry(null)).toBeNull();
	});

	it('splits prayers from answered prayers and hides tombstones', () => {
		const store = cleanStore({
			n: entry('n'),
			p: entry('p', { kind: 'prayer', createdAt: T0 + 1 }),
			a: entry('a', { kind: 'prayer', answeredAt: T0 + 5 * DAY }),
			d: tombstone(entry('d', { kind: 'prayer' }))
		});
		expect(journalStats(store)).toEqual({ notes: 1, prayers: 1, answered: 1 });
		expect(visibleEntries(store, 'prayers').map((e) => e.id)).toEqual(['p']);
		expect(visibleEntries(store, 'answered').map((e) => e.id)).toEqual(['a']);
		// Newest first.
		expect(visibleEntries(store).map((e) => e.id)).toEqual(['p', 'n', 'a']);
		expect(visibleEntries(store, 'all', 'P').map((e) => e.id)).toEqual(['p']);
	});

	it('a tombstone keeps no words', () => {
		const t = tombstone(entry('x', { title: 'secret', body: 'secret', answer: 'secret' }), T0 + 1);
		expect(t).toMatchObject({
			deleted: true,
			title: '',
			body: '',
			answer: '',
			updatedAt: T0 + 1
		});
	});

	it('counts the days a prayer was prayed', () => {
		expect(daysWaited(entry('p', { kind: 'prayer' }))).toBeNull();
		expect(daysWaited(entry('p', { kind: 'prayer', answeredAt: T0 + 2 * 3600_000 }))).toBe(0);
		expect(daysWaited(entry('p', { kind: 'prayer', answeredAt: T0 + 12 * DAY }))).toBe(12);
	});

	it('groups a sorted list under each day', () => {
		const list = [
			entry('a', { createdAt: T0 + DAY }),
			entry('b'),
			entry('c', { createdAt: T0 + 60_000 })
		];
		const groups = groupByDay(list);
		expect(groups.map((g) => g.entries.map((e) => e.id))).toEqual([['a'], ['b', 'c']]);
	});

	it("takes the account's journal except what this device still owes it", () => {
		const mine = entry('x', { body: 'typed offline', updatedAt: T0 + 5 });
		const theirs = entry('x', { body: 'account', updatedAt: T0 + 9 });
		// Owed: the local edit stands (its push delivers it) — whatever the clocks say.
		expect(applyServerJournal({ x: theirs }, { x: mine }, { x: T0 + 5 }).x.body).toBe('typed offline');
		// Not owed: the account is the truth, even over a local clock that ran ahead.
		expect(applyServerJournal({ x: theirs }, { x: { ...mine, updatedAt: T0 + 99 } }, {}).x.body).toBe('account');
		// A tombstone from the account is sticky; an entry it lacks is kept.
		const gone = tombstone(theirs);
		expect(applyServerJournal({ x: gone }, { x: mine }, { x: T0 + 5 }).x.deleted).toBe(true);
		expect(applyServerJournal({}, { y: entry('y') }, {}).y.body).toBe('y');
	});

	it('keeps prayer-list fields on prayers only, and only valid ones', () => {
		const store = cleanStore({
			p: entry('p', {
				kind: 'prayer',
				person: 'Anna',
				group: 'family',
				remind: 'weekly-0@07:30',
				updates: [{ at: T0, text: 'Interview Friday' }, { at: T0, text: '  ' }]
			}),
			bad: entry('bad', { kind: 'prayer', group: 'aliens' as never, remind: 'hourly@99:00' }),
			n: entry('n', { person: 'Anna', remind: 'daily@07:00' })
		});
		expect(store.p).toMatchObject({ person: 'Anna', group: 'family', remind: 'weekly-0@07:30' });
		expect(store.p.updates).toEqual([{ at: T0, text: 'Interview Friday' }]);
		expect(store.bad).toMatchObject({ group: '', remind: '' });
		expect(store.n).toMatchObject({ person: '', remind: '' });
	});

	it('accepts a source made of positions and nothing else', () => {
		const src = { kind: 'book', slug: 'humility', order: 2, p: 5, edition: 'en', title: 't', quote: 'q' };
		expect(cleanSource({ ...src, href: 'javascript:alert(1)' })).toEqual(src);
		expect(cleanSource({ ...src, slug: '../x' })).toBeNull();
		expect(cleanSource({ ...src, order: 0 })).toBeNull();
	});

	it('gathers open prayers under who they are for', () => {
		const store = cleanStore({
			a: entry('a', { kind: 'prayer', person: 'Anna', group: 'family', createdAt: T0 + 3 }),
			b: entry('b', { kind: 'prayer', person: 'anna ', remind: 'daily@07:00', createdAt: T0 + 1 }),
			c: entry('c', { kind: 'prayer', person: 'Gulu church', createdAt: T0 + 2 }),
			d: entry('d', { kind: 'prayer', createdAt: T0 + 4 }),
			done: entry('done', { kind: 'prayer', person: 'Dad', answeredAt: T0 + 5 })
		});
		const cards = prayersByPerson(store);
		expect(cards.map((c) => c.person)).toEqual(['Anna', 'Gulu church', '']);
		expect(cards[0]).toMatchObject({ group: 'family', remind: 'daily@07:00' });
		expect(cards[0].prayers.map((p) => p.id)).toEqual(['a', 'b']);
		expect(knownPeople(store)).toEqual(['Anna', 'Dad', 'Gulu church']);
	});

	it('reads and writes reminders', () => {
		expect(parseRemind('weekly-3@09:15')).toEqual({ freq: 'weekly', day: 3, time: '09:15' });
		expect(parseRemind('')).toBeNull();
		expect(formatRemind('daily', 4, '07:00')).toBe('daily@07:00');
		expect(formatRemind('weekly', 4, '07:00')).toBe('weekly-4@07:00');
	});

	it('round-trips through the server shape, and a tombstone keeps no words', () => {
		const e = cleanEntry({
			...entry('p', { kind: 'prayer', person: 'Anna', updates: [{ at: T0, text: 'u' }] }),
			answeredAt: T0 + DAY,
			answer: 'yes'
		})!;
		const back = fromServer({
			...toServer(e),
			answered_at: new Date(T0 + DAY).toISOString(),
			client_created_at: new Date(T0).toISOString(),
			client_updated_at: new Date(T0).toISOString()
		});
		expect(back).toEqual(e);
		const gone = fromServer({ ...toServer(e), deleted: true });
		expect(gone).toMatchObject({ deleted: true, body: '', person: '', answer: '', updates: [] });
	});

	it('keeps a daily prayer like a note and out of the prayer list', () => {
		const store = cleanStore({
			d: entry('d', { kind: 'daily', person: 'Anna', answeredAt: T0 } as Partial<JournalEntry>)
		});
		expect(store.d).toMatchObject({ kind: 'daily', person: '', answeredAt: null });
		expect(journalStats(store)).toEqual({ notes: 0, prayers: 0, answered: 0 });
		expect(visibleEntries(store, 'prayers')).toEqual([]);
		expect(visibleEntries(store, 'all').map((e) => e.id)).toEqual(['d']);
	});

	it('counts daily prayers in a row, and whether today is done', () => {
		const at = (iso: string) => new Date(`${iso}T09:00:00`).getTime();
		const store = cleanStore({
			a: entry('a', { kind: 'daily', createdAt: at('2026-09-20') }),
			b: entry('b', { kind: 'daily', createdAt: at('2026-09-21') }),
			n: entry('n', { createdAt: at('2026-09-22') })
		});
		expect(dailyStreak(store, '2026-09-22')).toEqual({ streak: 2, doneToday: false });
		expect(dailyStreak(store, '2026-09-21')).toEqual({ streak: 2, doneToday: true });
		expect(dailyStreak(store, '2026-09-24')).toEqual({ streak: 0, doneToday: false });
	});

	it('gives each movement a verse for the day that changes the next day', () => {
		expect(dailyVerse('adore', '2026-09-22')).toBe(dailyVerse('adore', '2026-09-22'));
		expect(dailyVerse('adore', '2026-09-22')).not.toBe(dailyVerse('adore', '2026-09-23'));
		expect(dailyVerse('ask', '2026-09-22')).toMatch(/\d+:\d+$/);
	});

	it('writes the movements under their names, skipping the empty ones', () => {
		const names = { adore: 'Adore', confess: 'Confess', thanks: 'Thanks', ask: 'Ask' };
		expect(composeDaily({ adore: ' You are good. ', confess: '  ', ask: 'Anna — the job' }, names)).toBe(
			'Adore\nYou are good.\n\nAsk\nAnna — the job'
		);
		expect(composeDaily({}, names)).toBe('');
	});
});
