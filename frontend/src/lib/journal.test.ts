import { describe, it, expect } from 'vitest';
import {
	cleanEntry,
	cleanSource,
	collectionsOf,
	inCollection,
	composeDaily,
	dailyStreak,
	dailyVerse,
	faithfulness,
	monthsBack,
	onThisDay,
	journalForPrint,
	periodStart,
	cleanStore,
	formatRemind,
	fromServer,
	toServer,
	knownPeople,
	parseRemind,
	prayersByGroup,
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
		collection: '',
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

	it('keeps the record of answered prayers, month by month', () => {
		const at = (iso: string) => new Date(`${iso}T12:00:00`).getTime();
		const store = cleanStore({
			a: entry('a', { kind: 'prayer', createdAt: at('2026-09-01'), answeredAt: at('2026-09-14'), body: 'Dad' }),
			b: entry('b', { kind: 'prayer', createdAt: at('2026-09-20'), answeredAt: at('2026-09-20'), body: 'books' }),
			c: entry('c', { kind: 'prayer', createdAt: at('2026-01-01'), answeredAt: at('2026-03-13'), body: 'visa' }),
			open: entry('open', { kind: 'prayer', body: 'rain' }),
			gone: tombstone(entry('gone', { kind: 'prayer', answeredAt: at('2026-09-02') }))
		});
		const f = faithfulness(store);
		expect(f).toMatchObject({ answered: 3, praying: 1, avgDays: Math.round((13 + 0 + 71) / 3) });
		expect(f.months.map((m) => [m.month, m.prayers.map((p) => p.id)])).toEqual([
			['2026-09', ['b', 'a']],
			['2026-03', ['c']]
		]);
		// A search narrows the timeline, not the totals.
		expect(faithfulness(store, 'visa').months.map((m) => m.month)).toEqual(['2026-03']);
		expect(faithfulness(cleanStore({})).avgDays).toBeNull();
	});

	it('finds the same day months and years back, never a neighbouring one', () => {
		expect(monthsBack('2026-09-23', 1)).toBe('2026-08-23');
		expect(monthsBack('2026-01-15', 3)).toBe('2025-10-15');
		expect(monthsBack('2026-03-31', 1)).toBeNull(); // no 31 February
		expect(monthsBack('2028-02-29', 12)).toBeNull(); // 2027 is no leap year
		expect(monthsBack('2026-09-23', 24)).toBe('2024-09-23');
	});

	it('remembers what was written and answered on this day', () => {
		const at = (iso: string) => new Date(`${iso}T10:00:00`).getTime();
		const store = cleanStore({
			yearNote: entry('yearNote', { createdAt: at('2025-09-23'), body: 'a year ago' }),
			monthPrayer: entry('monthPrayer', { kind: 'prayer', createdAt: at('2026-08-23') }),
			answered: entry('answered', {
				kind: 'prayer',
				createdAt: at('2025-01-02'),
				answeredAt: at('2026-06-23')
			}),
			both: entry('both', { kind: 'prayer', createdAt: at('2025-09-23'), answeredAt: at('2026-08-23') }),
			other: entry('other', { createdAt: at('2026-09-22') }),
			gone: tombstone(entry('gone', { createdAt: at('2026-08-23') }))
		});
		const mem = onThisDay(store, '2026-09-23', 10);
		expect(mem.map((x) => [x.entry.id, x.what, x.ago.unit, x.ago.n])).toEqual([
			['both', 'answered', 'month', 1],
			['monthPrayer', 'written', 'month', 1],
			['answered', 'answered', 'month', 3],
			['yearNote', 'written', 'year', 1]
		]);
		expect(onThisDay(store, '2026-09-23')).toHaveLength(3);
		expect(onThisDay(store, '2026-09-24')).toEqual([]);
	});

	it('lays the journal out as a book for the chosen period, oldest first', () => {
		const at = (iso: string) => new Date(`${iso}T10:00:00`).getTime();
		const store = cleanStore({
			n1: entry('n1', { createdAt: at('2026-09-10') }),
			n0: entry('n0', { createdAt: at('2026-02-01') }),
			old: entry('old', { createdAt: at('2025-05-01') }),
			a1: entry('a1', { kind: 'prayer', createdAt: at('2025-12-01'), answeredAt: at('2026-09-02') }),
			a0: entry('a0', { kind: 'prayer', createdAt: at('2026-01-01'), answeredAt: at('2026-03-05') }),
			p1: entry('p1', { kind: 'prayer', person: 'Anna', createdAt: at('2026-09-01') }),
			p0: entry('p0', { kind: 'prayer', person: 'Anna', createdAt: at('2026-08-01') }),
			d: entry('d', { kind: 'daily', createdAt: at('2026-09-20') }),
			gone: tombstone(entry('gone', { createdAt: at('2026-09-11') }))
		});
		const year = journalForPrint(store, periodStart('year', new Date('2026-09-23T12:00:00')));
		expect(year.notes.map((e) => e.id)).toEqual(['n0', 'n1']);
		// Answered in the year counts, even though it was asked the year before.
		expect(year.answered.map((m) => [m.month, m.prayers.map((e) => e.id)])).toEqual([
			['2026-03', ['a0']],
			['2026-09', ['a1']]
		]);
		expect(year.praying.map((c) => [c.person, c.prayers.map((e) => e.id)])).toEqual([['Anna', ['p0', 'p1']]]);
		expect(year.daily.map((e) => e.id)).toEqual(['d']);
		expect(journalForPrint(store, 0).notes.map((e) => e.id)).toEqual(['old', 'n0', 'n1']);
		expect(periodStart('month', new Date('2026-09-23T12:00:00'))).toBe(new Date(2026, 8, 1).getTime());
	});

	it('gathers the prayer lists by group, in the offered order, ungrouped last', () => {
		const store = cleanStore({
			a: entry('a', { kind: 'prayer', person: 'Anna', group: 'family', createdAt: T0 + 3 }),
			m: entry('m', { kind: 'prayer', person: 'Gulu church', group: 'missions', createdAt: T0 + 2 }),
			m2: entry('m2', { kind: 'prayer', person: 'Gulu church', group: 'missions', createdAt: T0 + 1 }),
			x: entry('x', { kind: 'prayer', person: 'Sam', createdAt: T0 + 4 }),
			done: entry('done', { kind: 'prayer', person: 'Dad', group: 'family', answeredAt: T0 + 5 })
		});
		const lists = prayersByGroup(store);
		expect(lists.map((l) => [l.group, l.count, l.cards.map((c) => c.person)])).toEqual([
			['family', 1, ['Anna']],
			['missions', 2, ['Gulu church']],
			['', 1, ['Sam']]
		]);
		expect(prayersByGroup(store, 'gulu').map((l) => l.group)).toEqual(['missions']);
	});

	it('lists collections, matched whatever their case, most recently used first', () => {
		const store = cleanStore({
			a: entry('a', { collection: 'Notes on Humility', updatedAt: T0 + 1 }),
			b: entry('b', { collection: '  notes on humility ', updatedAt: T0 + 9 }),
			r: entry('r', { collection: 'Romans study', updatedAt: T0 + 5 }),
			gone: tombstone(entry('gone', { collection: 'Romans study' })),
			loose: entry('loose')
		});
		expect(collectionsOf(store)).toEqual([
			{ name: 'Notes on Humility', count: 2, updatedAt: T0 + 9 },
			{ name: 'Romans study', count: 1, updatedAt: T0 + 5 }
		]);
		expect(inCollection(store.b, 'NOTES ON HUMILITY')).toBe(true);
		expect(inCollection(store.loose, '')).toBe(false);
		expect(visibleEntries(store, 'all', 'romans').map((e) => e.id)).toEqual(['r']);
	});
});
