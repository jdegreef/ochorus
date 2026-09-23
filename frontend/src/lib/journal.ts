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

import { localToday } from './streak';

export type JournalKind = 'note' | 'prayer';

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
	if (o.kind !== 'note' && o.kind !== 'prayer') return null;
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
		hay = [e.title, e.body, e.ref, e.answer, e.person, e.source?.quote ?? '', ...e.updates.map((u) => u.text)]
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
