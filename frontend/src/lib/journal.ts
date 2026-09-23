/**
 * The Notebook's own writing — notes and prayers — as plain data.
 *
 * Everything else in the Notebook is a place in a TEXT (a highlight, a
 * bookmark); a journal entry is the reader's own words. A prayer becomes an
 * answered prayer by gaining `answeredAt` (and, optionally, `answer`: how it
 * was answered) — the same entry, so the request and its answer stay together.
 *
 * Pure: no storage, no Svelte. The reactive store is `journal.svelte.ts`; the
 * account copy is `reading/JournalEntry` on the server, synced last-write-wins
 * by `updatedAt`, with deletes kept as tombstones so an offline device can't
 * bring a deleted prayer back (see readingSync).
 */

import { currentStreak, localToday } from './streak';

/** A note; a prayer (a request that can be answered); or the day's guided
 *  prayer — the reader's own words for the day, carrying no prayer-list fields. */
export type JournalKind = 'note' | 'prayer' | 'daily';

/** The prayer-list groups, in the order the Notebook offers them (the server's
 *  reading.models.PrayerGroup holds the same values). */
export const PRAYER_GROUPS = ['family', 'friends', 'church', 'missions', 'work', 'world'] as const;
export type PrayerGroup = (typeof PRAYER_GROUPS)[number];

/** A dated follow-up on a prayer ("Interview moved to Friday"). */
export interface PrayerUpdate {
	at: number;
	text: string;
}

/**
 * The passage an entry was written from, when it began as a highlight in the
 * reader. Positions, never a URL: the link back is built from these parts
 * (see `sourceHref`), so nothing stored or synced can become an arbitrary href.
 */
export interface EntrySource {
	kind: 'book' | 'sermon' | 'bio';
	slug: string;
	order: number;
	p: number;
	edition: string;
	/** "Humility · Chapter 2" — display only. */
	title: string;
	quote: string;
}

export interface JournalEntry {
	/** Client-minted, URL-safe (`newEntryId`); the server keys on it. */
	id: string;
	kind: JournalKind;
	title: string;
	body: string;
	/** Optional Scripture / passage the entry is about ("Psalm 23"). */
	ref: string;
	/** The collection it is filed in ("Notes on Humility"), or ''. */
	collection: string;
	/** When it was pinned to the top of the Notebook; null when it isn't. */
	pinnedAt: number | null;
	/** Who or what a prayer is for ("Anna", "Gulu church"). Prayers only. */
	person: string;
	group: PrayerGroup | '';
	/** A calendar reminder the reader added: "daily@07:00", "weekly-0@09:00" (0 = Sunday), or ''. */
	remind: string;
	updates: PrayerUpdate[];
	source: EntrySource | null;
	/** How a prayer was answered, in the reader's words. */
	answer: string;
	/** Epoch ms the prayer was marked answered; null while still praying. */
	answeredAt: number | null;
	createdAt: number;
	updatedAt: number;
	/** A tombstone: kept (without its text) so the delete syncs. */
	deleted?: boolean;
}

/** id → entry, tombstones included. */
export type JournalStore = Record<string, JournalEntry>;

/** Column bounds, mirrored from the server so a long entry isn't cut silently. */
export const TITLE_MAX = 200;
export const BODY_MAX = 20_000;
export const ANSWER_MAX = 10_000;
export const REF_MAX = 200;
export const PERSON_MAX = 80;
export const COLLECTION_MAX = 80;
export const UPDATE_MAX = 2_000;
const MAX_UPDATES = 50;

const ID_RE = /^[A-Za-z0-9_-]{1,64}$/;
const SLUG_RE = /^[A-Za-z0-9_-]{1,160}$/;
// Groups: 1 = frequency word, 2 = weekday (weekly only), 3 = HH:MM.
const REMIND_RE = /^(daily|weekly-([0-6]))@((?:[01]\d|2[0-3]):[0-5]\d)$/;

export function newEntryId(now = Date.now(), rand = Math.random): string {
	return `${now.toString(36)}-${rand().toString(36).slice(2, 10) || '0'}`;
}

const str = (v: unknown, n: number) => (typeof v === 'string' ? v.slice(0, n) : '');
const ms = (v: unknown): number | null =>
	typeof v === 'number' && Number.isFinite(v) && v > 0 ? v : null;

function cleanUpdates(v: unknown): PrayerUpdate[] {
	if (!Array.isArray(v)) return [];
	const out: PrayerUpdate[] = [];
	for (const u of v.slice(0, MAX_UPDATES)) {
		const at = ms((u as PrayerUpdate)?.at);
		const text = str((u as PrayerUpdate)?.text, UPDATE_MAX);
		if (at && text.trim()) out.push({ at, text });
	}
	return out;
}

export function cleanSource(v: unknown): EntrySource | null {
	if (!v || typeof v !== 'object') return null;
	const o = v as Record<string, unknown>;
	if (o.kind !== 'book' && o.kind !== 'sermon' && o.kind !== 'bio') return null;
	if (typeof o.slug !== 'string' || !SLUG_RE.test(o.slug)) return null;
	if (!Number.isInteger(o.order) || (o.order as number) < 1) return null;
	if (!Number.isInteger(o.p) || (o.p as number) < 0) return null;
	if (typeof o.edition !== 'string' || !o.edition || o.edition.length > 16) return null;
	return {
		kind: o.kind,
		slug: o.slug,
		order: o.order as number,
		p: o.p as number,
		edition: o.edition,
		title: str(o.title, 200),
		quote: str(o.quote, 600)
	};
}

/**
 * One stored / synced value → a well-formed entry, or null. localStorage and
 * the server are both outside this module's control, so every field is
 * re-checked rather than trusted — a corrupt row is dropped, never rendered.
 */
export function cleanEntry(v: unknown): JournalEntry | null {
	if (!v || typeof v !== 'object') return null;
	const o = v as Record<string, unknown>;
	if (typeof o.id !== 'string' || !ID_RE.test(o.id)) return null;
	if (o.kind !== 'note' && o.kind !== 'prayer' && o.kind !== 'daily') return null;
	const createdAt = ms(o.createdAt) ?? ms(o.updatedAt) ?? Date.now();
	const updatedAt = ms(o.updatedAt) ?? createdAt;
	// A tombstone keeps its identity and clock, never the reader's words — the
	// one place that rule lives on this side (the server's is _journal_fields).
	if (o.deleted === true) {
		return { ...BLANK, id: o.id, kind: o.kind, createdAt, updatedAt, deleted: true };
	}
	const prayer = o.kind === 'prayer';
	const answeredAt = prayer ? ms(o.answeredAt) : null;
	return {
		id: o.id,
		kind: o.kind,
		title: str(o.title, TITLE_MAX),
		body: str(o.body, BODY_MAX),
		ref: str(o.ref, REF_MAX),
		collection: str(o.collection, 200).trim().slice(0, COLLECTION_MAX),
		pinnedAt: ms(o.pinnedAt),
		person: prayer ? str(o.person, PERSON_MAX) : '',
		group: prayer && PRAYER_GROUPS.includes(o.group as PrayerGroup) ? (o.group as PrayerGroup) : '',
		remind: prayer && typeof o.remind === 'string' && REMIND_RE.test(o.remind) ? o.remind : '',
		updates: prayer ? cleanUpdates(o.updates) : [],
		source: cleanSource(o.source),
		answer: answeredAt ? str(o.answer, ANSWER_MAX) : '',
		answeredAt,
		createdAt,
		updatedAt
	};
}

const BLANK = {
	collection: '',
	pinnedAt: null,
	title: '',
	body: '',
	ref: '',
	person: '',
	group: '',
	remind: '',
	updates: [],
	source: null,
	answer: '',
	answeredAt: null
} as const satisfies Partial<JournalEntry>;

/** A whole stored blob → a clean store (junk rows dropped). */
export function cleanStore(v: unknown): JournalStore {
	const out: JournalStore = {};
	if (!v || typeof v !== 'object' || Array.isArray(v)) return out;
	for (const raw of Object.values(v)) {
		const e = cleanEntry(raw);
		if (e) out[e.id] = e;
	}
	return out;
}

/** The tombstone a delete leaves: identity + clock, no text. */
export function tombstone(e: JournalEntry, now = Date.now()): JournalEntry {
	return cleanEntry({ ...e, deleted: true, updatedAt: now })!;
}

/** Which slice of the journal a Notebook tab shows. */
export type JournalFilter = 'all' | 'notes' | 'prayers' | 'answered';

function matchesFilter(e: JournalEntry, f: JournalFilter): boolean {
	if (f === 'notes') return e.kind === 'note';
	// "Prayers" are the ones still being prayed; answered ones have their own page.
	if (f === 'prayers') return e.kind === 'prayer' && !e.answeredAt;
	if (f === 'answered') return e.kind === 'prayer' && !!e.answeredAt;
	return true;
}

// Each entry's lowercased search text, built once per entry object: the store
// keeps an unchanged entry's identity, so typing in the search box doesn't
// rebuild (up to) 20k characters of text per entry per keystroke.
const searchText = new WeakMap<JournalEntry, string>();

function matchesQuery(e: JournalEntry, q: string): boolean {
	if (!q) return true;
	let hay = searchText.get(e);
	if (hay === undefined) {
		hay = [e.title, e.body, e.ref, e.collection, e.answer, e.person, e.source?.quote ?? '', ...e.updates.map((u) => u.text)]
			.join('\n')
			.toLowerCase();
		searchText.set(e, hay);
	}
	return hay.includes(q.toLowerCase());
}

/** When an entry sits in its list: answered prayers file under the day they
 *  were answered — the day worth remembering on that page — the rest under
 *  the day they were written. */
export function entryTime(e: JournalEntry, filter: JournalFilter): number {
	return filter === 'answered' && e.answeredAt ? e.answeredAt : e.createdAt;
}

/** Live entries, newest first — answered prayers by when they were answered. */
export function visibleEntries(
	store: JournalStore,
	filter: JournalFilter = 'all',
	q = ''
): JournalEntry[] {
	return Object.values(store)
		.filter((e) => !e.deleted && matchesFilter(e, filter) && matchesQuery(e, q))
		.sort((a, b) => entryTime(b, filter) - entryTime(a, filter));
}

interface JournalStats {
	notes: number;
	prayers: number;
	answered: number;
}

export function journalStats(store: JournalStore): JournalStats {
	const s: JournalStats = { notes: 0, prayers: 0, answered: 0 };
	for (const e of Object.values(store)) {
		if (e.deleted) continue;
		if (e.kind === 'note') s.notes += 1;
		else if (e.kind !== 'prayer') continue; // a daily prayer is neither
		else if (e.answeredAt) s.answered += 1;
		else s.prayers += 1;
	}
	return s;
}

const DAY = 86_400_000;

/** Whole days a prayer was prayed before its answer (0 = the same day). */
export function daysWaited(e: JournalEntry): number | null {
	if (!e.answeredAt) return null;
	return Math.max(0, Math.round((e.answeredAt - e.createdAt) / DAY));
}

/** Group an already-sorted list under its local calendar day, keeping the order. */
export function groupByDay(
	list: JournalEntry[],
	at: (e: JournalEntry) => number = (e) => e.createdAt
): { day: string; at: number; entries: JournalEntry[] }[] {
	const out: { day: string; at: number; entries: JournalEntry[] }[] = [];
	for (const e of list) {
		const t = at(e);
		const day = localToday(new Date(t));
		const last = out[out.length - 1];
		if (last && last.day === day) last.entries.push(e);
		else out.push({ day, at: t, entries: [e] });
	}
	return out;
}

/**
 * The journal after a sign-in merge: the account's copy is the truth, except
 * for what this device still owes it — an entry edited here that the account
 * has not confirmed (`pending`, id → the updatedAt written) keeps its local
 * version, since its own push or the next merge will deliver it; and an entry
 * the account doesn't have at all is kept rather than lost. A tombstone from
 * the account is sticky, as it is on the server.
 */
export function applyServerJournal(
	server: JournalStore,
	local: JournalStore,
	pending: Record<string, number>
): JournalStore {
	const out: JournalStore = { ...server };
	for (const [id, e] of Object.entries(local)) {
		const theirs = server[id];
		if (!theirs || (id in pending && !theirs.deleted)) out[id] = e;
	}
	return out;
}

/** One card of the "by person" prayer list: everyone a prayer names, grouped. */
export interface PersonGroup {
	/** Display name; '' collects the prayers that name no one. */
	person: string;
	group: PrayerGroup | '';
	prayers: JournalEntry[];
	/** The reminder shown on the card — the first of its prayers that has one. */
	remind: string;
	updates: number;
}

/**
 * Still-open prayers gathered under who they are for. Names match
 * case-insensitively ("anna" and "Anna" are one card), the card takes the
 * group its newest prayer gives, and cards order by their most recent prayer
 * — the people on your heart lately come first. Prayers for no one in
 * particular come last.
 */
export function prayersByPerson(store: JournalStore, q = ''): PersonGroup[] {
	const cards = new Map<string, PersonGroup>();
	for (const e of visibleEntries(store, 'prayers', q)) {
		const key = e.person.trim().toLowerCase();
		let card = cards.get(key);
		if (!card) {
			card = { person: e.person.trim(), group: e.group, prayers: [], remind: '', updates: 0 };
			cards.set(key, card);
		}
		card.prayers.push(e);
		card.remind ||= e.remind;
		card.updates += e.updates.length;
	}
	return [...cards.values()].sort((a, b) => Number(a.person === '') - Number(b.person === ''));
}

/** Everyone the reader has prayed for, for the composer's suggestions. */
export function knownPeople(store: JournalStore): string[] {
	const seen = new Map<string, string>();
	for (const e of Object.values(store)) {
		const name = e.person.trim();
		if (!e.deleted && name && !seen.has(name.toLowerCase())) seen.set(name.toLowerCase(), name);
	}
	return [...seen.values()].sort((a, b) => a.localeCompare(b));
}

/** A reminder as its parts, or null when there is none. */
export function parseRemind(r: string): { freq: 'daily' | 'weekly'; day: number; time: string } | null {
	const m = REMIND_RE.exec(r);
	if (!m) return null;
	return m[2] === undefined
		? { freq: 'daily', day: 0, time: m[3] }
		: { freq: 'weekly', day: Number(m[2]), time: m[3] };
}

export function formatRemind(freq: 'daily' | 'weekly', day: number, time: string): string {
	return freq === 'daily' ? `daily@${time}` : `weekly-${day}@${time}`;
}

/** An entry as the account API carries it (reading/serializers JournalEntrySerializer). */
export interface ServerJournalEntry {
	entry_id: string;
	kind: string;
	title: string;
	body: string;
	answer: string;
	answered_at: string | number | null;
	ref: string;
	collection?: string;
	pinned_at?: string | number | null;
	person?: string;
	group?: string;
	remind?: string;
	updates?: PrayerUpdate[];
	source?: unknown;
	deleted: boolean;
	client_created_at: string | number;
	client_updated_at: string | number;
}

/** To the server's shape. Clocks go as epoch ms; the server parses them. The
 *  one field list, beside its inverse, so a field can't sync one way only. */
export function toServer(e: JournalEntry): ServerJournalEntry {
	return {
		entry_id: e.id,
		kind: e.kind,
		title: e.title,
		body: e.body,
		ref: e.ref,
		collection: e.collection,
		pinned_at: e.pinnedAt,
		person: e.person,
		group: e.group,
		remind: e.remind,
		updates: e.updates,
		source: e.source,
		answer: e.answer,
		answered_at: e.answeredAt,
		deleted: e.deleted === true,
		client_created_at: e.createdAt,
		client_updated_at: e.updatedAt
	};
}

/** From the server's shape (ISO datetimes), through the same cleaner as storage. */
export function fromServer(j: ServerJournalEntry): JournalEntry | null {
	const at = (v: string | number | null) => (typeof v === 'string' ? Date.parse(v) || null : v);
	return cleanEntry({
		id: j.entry_id,
		kind: j.kind,
		title: j.title,
		body: j.body,
		ref: j.ref,
		collection: j.collection,
		pinnedAt: at(j.pinned_at ?? null),
		person: j.person,
		group: j.group,
		remind: j.remind,
		updates: j.updates,
		source: j.source,
		answer: j.answer,
		answeredAt: at(j.answered_at),
		createdAt: at(j.client_created_at),
		updatedAt: at(j.client_updated_at),
		deleted: j.deleted
	});
}

/** The four movements of the guided daily prayer (ACTS), in order. */
export const DAILY_STEPS = ['adore', 'confess', 'thanks', 'ask'] as const;
export type DailyStep = (typeof DAILY_STEPS)[number];

/**
 * A Scripture to open each movement with — seven apiece, so a week of days
 * never repeats one. References only: the words come from the Scripture API
 * (see `$lib/scripture.svelte`), and a reference is language-neutral data.
 */
const DAILY_VERSES: Record<DailyStep, readonly string[]> = {
	adore: ['Psalm 103:1', 'Psalm 145:3', 'Isaiah 6:3', 'Psalm 95:6', 'Revelation 4:11', 'Psalm 34:8', 'Psalm 96:9'],
	confess: ['1 John 1:9', 'Psalm 51:10', 'Psalm 139:23', 'Proverbs 28:13', 'Psalm 32:5', 'Isaiah 1:18', 'James 5:16'],
	thanks: ['Psalm 100:4', '1 Thessalonians 5:18', 'Psalm 107:1', 'Colossians 3:15', 'Psalm 136:1', 'James 1:17', 'Lamentations 3:22'],
	ask: ['Philippians 4:6', 'Matthew 7:7', 'John 14:13', 'Hebrews 4:16', '1 Peter 5:7', 'James 1:5', 'Psalm 5:3']
};

/** Today's verse for a movement: the same all day, a different one tomorrow. */
export function dailyVerse(step: DailyStep, today: string): string {
	const day = Math.floor(Date.parse(`${today}T00:00:00Z`) / DAY);
	const list = DAILY_VERSES[step];
	return list[((day % list.length) + list.length) % list.length];
}

/** The local days the reader prayed the daily prayer. */
function dailyDays(store: JournalStore): Set<string> {
	const days = new Set<string>();
	for (const e of Object.values(store)) {
		if (!e.deleted && e.kind === 'daily') days.add(localToday(new Date(e.createdAt)));
	}
	return days;
}

/** Days in a row with a daily prayer, and whether today's is done. */
export function dailyStreak(store: JournalStore, today: string): { streak: number; doneToday: boolean } {
	const days = dailyDays(store);
	return { streak: currentStreak(days, today), doneToday: days.has(today) };
}

/**
 * The saved daily prayer's text: each movement the reader wrote in, under its
 * name, in order. Plain text on purpose — it reads the same in the Notebook,
 * the export and a synced device, and the card sets the names in bold.
 */
export function composeDaily(parts: Partial<Record<DailyStep, string>>, names: Record<DailyStep, string>): string {
	return DAILY_STEPS.filter((s) => parts[s]?.trim())
		.map((s) => `${names[s]}\n${parts[s]!.trim()}`)
		.join('\n\n');
}

/** One month of the faithfulness timeline: the prayers answered in it, newest first. */
export interface TimelineMonth {
	/** 'YYYY-MM' (local), the key. */
	month: string;
	/** A time inside the month, for its localized name. */
	at: number;
	prayers: JournalEntry[];
}

/**
 * The record of answered prayers — "stones of remembrance": how many, how
 * many are still being prayed, how long an answer took on average, and every
 * answer by the month it came. `q` searches like the rest of the Notebook.
 */
export function faithfulness(
	store: JournalStore,
	q = ''
): { answered: number; praying: number; avgDays: number | null; months: TimelineMonth[] } {
	const stats = journalStats(store);
	const answered = visibleEntries(store, 'answered', q);
	const waits = visibleEntries(store, 'answered').map((e) => daysWaited(e) ?? 0);
	const months: TimelineMonth[] = [];
	for (const e of answered) {
		const at = e.answeredAt!;
		const month = localToday(new Date(at)).slice(0, 7);
		const last = months[months.length - 1];
		if (last && last.month === month) last.prayers.push(e);
		else months.push({ month, at, prayers: [e] });
	}
	return {
		answered: stats.answered,
		praying: stats.prayers,
		avgDays: waits.length ? Math.round(waits.reduce((a, b) => a + b, 0) / waits.length) : null,
		months
	};
}

/** How long ago a remembered day was: months (1, 3, 6) or years (1, 2, …). */
export type Ago = { unit: 'month' | 'year'; n: number };

/** One memory for the "On this day" card. */
export interface Memory {
	entry: JournalEntry;
	ago: Ago;
	/** 'written' — the reader wrote it that day; 'answered' — God answered it that day. */
	what: 'written' | 'answered';
}

const MONTHS_BACK = [1, 3, 6];
const YEARS_BACK = 10;

/**
 * The same calendar day `months` months back from `today` ('YYYY-MM-DD'), or
 * null when that month has no such day (no 31 September) — a memory is kept
 * for its own date, never moved to a neighbour.
 */
export function monthsBack(today: string, months: number): string | null {
	const [y, m, d] = today.split('-').map(Number);
	const total = y * 12 + (m - 1) - months;
	const year = Math.floor(total / 12);
	const month = (total % 12) + 1;
	const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
	if (d > last) return null;
	return `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

/**
 * What the reader wrote — and what God answered — on this day one, three and
 * six months ago, and on this date in every past year: the Notebook's "On this
 * day". Nearest first; within a day, answers before writing (they are the
 * better news). Daily prayers are included; tombstones never are.
 */
export function onThisDay(store: JournalStore, today: string, limit = 3): Memory[] {
	const anniversaries = new Map<string, Ago>();
	for (const n of MONTHS_BACK) {
		const day = monthsBack(today, n);
		if (day) anniversaries.set(day, { unit: 'month', n });
	}
	for (let n = 1; n <= YEARS_BACK; n++) {
		const day = monthsBack(today, n * 12);
		if (day) anniversaries.set(day, { unit: 'year', n });
	}
	const out: Memory[] = [];
	for (const e of Object.values(store)) {
		if (e.deleted) continue;
		const answered = e.answeredAt ? anniversaries.get(localToday(new Date(e.answeredAt))) : undefined;
		if (answered) out.push({ entry: e, ago: answered, what: 'answered' });
		const written = anniversaries.get(localToday(new Date(e.createdAt)));
		// A prayer both written and answered on remembered days shows once, as the answer.
		if (written && !answered) out.push({ entry: e, ago: written, what: 'written' });
	}
	const months = (a: Ago) => (a.unit === 'month' ? a.n : a.n * 12);
	return out
		.sort(
			(a, b) =>
				months(a.ago) - months(b.ago) ||
				Number(b.what === 'answered') - Number(a.what === 'answered') ||
				b.entry.createdAt - a.entry.createdAt
		)
		.slice(0, limit);
}

/** Which stretch of the journal to print. */
export type PrintPeriod = 'all' | 'year' | 'last12' | 'month';

/** The first moment of a period ending at `now`, or 0 for all time. */
export function periodStart(period: PrintPeriod, now: Date): number {
	if (period === 'year') return new Date(now.getFullYear(), 0, 1).getTime();
	if (period === 'month') return new Date(now.getFullYear(), now.getMonth(), 1).getTime();
	if (period === 'last12') return new Date(now.getFullYear() - 1, now.getMonth(), now.getDate()).getTime();
	return 0;
}

/**
 * The journal as a printed book: each part in reading order (oldest first),
 * limited to what happened since `from`. An answered prayer belongs to the
 * period it was ANSWERED in — that is the page it is remembered on; everything
 * else to when it was written.
 */
export function journalForPrint(store: JournalStore, from: number) {
	const live = Object.values(store).filter((e) => !e.deleted);
	const oldestFirst = (at: (e: JournalEntry) => number) => (a: JournalEntry, b: JournalEntry) => at(a) - at(b);
	const answered = live
		.filter((e) => e.kind === 'prayer' && e.answeredAt && e.answeredAt >= from)
		.sort(oldestFirst((e) => e.answeredAt!));
	const inPeriod = (e: JournalEntry) => e.createdAt >= from;
	const openStore: JournalStore = Object.fromEntries(
		live.filter((e) => e.kind === 'prayer' && !e.answeredAt && inPeriod(e)).map((e) => [e.id, e])
	);
	// Still praying, by person as the prayer list has them; within a person, oldest first.
	const praying = prayersByPerson(openStore).map((c) => ({ ...c, prayers: [...c.prayers].reverse() }));
	const notes = live.filter((e) => e.kind === 'note' && inPeriod(e)).sort(oldestFirst((e) => e.createdAt));
	const daily = live.filter((e) => e.kind === 'daily' && inPeriod(e)).sort(oldestFirst((e) => e.createdAt));
	const months: TimelineMonth[] = [];
	for (const e of answered) {
		const month = localToday(new Date(e.answeredAt!)).slice(0, 7);
		const last = months[months.length - 1];
		if (last && last.month === month) last.prayers.push(e);
		else months.push({ month, at: e.answeredAt!, prayers: [e] });
	}
	return { answered: months, answeredCount: answered.length, praying, notes, daily };
}

/** One prayer list: a group and the people in it, as the "by person" cards. */
export interface PrayerList {
	/** '' collects the prayers in no group. */
	group: PrayerGroup | '';
	cards: PersonGroup[];
	/** Open prayers in the list. */
	count: number;
}

/**
 * The prayer lists — Family, Friends, Church, Missions, Work, The world — each
 * holding its people's still-open prayers, in the order the Notebook offers
 * the groups; the prayers in no group come last. A person sits in the list of
 * their card's group (the group their newest prayer gives). Empty lists are
 * left out.
 */
export function prayersByGroup(store: JournalStore, q = ''): PrayerList[] {
	const lists = new Map<PrayerGroup | '', PersonGroup[]>();
	for (const card of prayersByPerson(store, q)) {
		const list = lists.get(card.group) ?? [];
		list.push(card);
		lists.set(card.group, list);
	}
	return [...PRAYER_GROUPS, '' as const]
		.filter((g) => lists.has(g))
		.map((group) => {
			const cards = lists.get(group)!;
			return { group, cards, count: cards.reduce((n, c) => n + c.prayers.length, 0) };
		});
}

/** A collection: the entries filed under one name. */
export interface Collection {
	name: string;
	count: number;
	/** When something in it was last written or changed. */
	updatedAt: number;
}

/** Collection names match whatever their case: "romans" and "Romans" are one. */
const collectionKey = (name: string) => name.trim().toLocaleLowerCase();

export function sameCollection(a: string, b: string): boolean {
	return !!a && collectionKey(a) === collectionKey(b);
}

export function inCollection(e: JournalEntry, name: string): boolean {
	return sameCollection(e.collection, name);
}

/**
 * Every collection the reader has, most recently used first — the name as it
 * was first written, and how many live entries are in it.
 */
export function collectionsOf(store: JournalStore): Collection[] {
	const out = new Map<string, Collection>();
	for (const e of Object.values(store)) {
		if (e.deleted || !e.collection) continue;
		const key = collectionKey(e.collection);
		const c = out.get(key);
		if (c) {
			c.count += 1;
			c.updatedAt = Math.max(c.updatedAt, e.updatedAt);
		} else out.set(key, { name: e.collection, count: 1, updatedAt: e.updatedAt });
	}
	return [...out.values()].sort((a, b) => b.updatedAt - a.updatedAt);
}

/**
 * A list split for the page: what is pinned, most recently pinned first, and
 * the rest in the order given — so a pinned entry sits at the top once rather
 * than twice.
 */
export function splitPinned(list: JournalEntry[]): { pinned: JournalEntry[]; rest: JournalEntry[] } {
	const pinned = list.filter((e) => e.pinnedAt).sort((a, b) => b.pinnedAt! - a.pinnedAt!);
	return { pinned, rest: list.filter((e) => !e.pinnedAt) };
}

/**
 * The reader's reflection on one place — a plan day's chapter, a sermon's
 * study question — if they have written one: the newest live entry written
 * from that work (and chapter) under that title. The title is the question
 * or the day, so one sermon's several questions each find their own answer.
 */
export function reflectionFor(
	store: JournalStore,
	place: { kind: EntrySource['kind']; slug: string; order: number },
	title: string
): JournalEntry | undefined {
	const want = title.trim();
	let found: JournalEntry | undefined;
	for (const e of Object.values(store)) {
		const s = e.source;
		if (e.deleted || !s || s.kind !== place.kind || s.slug !== place.slug || s.order !== place.order) continue;
		if (e.title.trim() !== want) continue;
		if (!found || e.createdAt > found.createdAt) found = e;
	}
	return found;
}

/** Which of the plan reflection prompts a day asks — they take turns, day by day. */
export const REFLECT_PROMPTS = 4;
export function reflectPrompt(day: number): number {
	return (((day - 1) % REFLECT_PROMPTS) + REFLECT_PROMPTS) % REFLECT_PROMPTS + 1;
}
