import { ERAS, eraOf, type EraId } from './eras';
import { longestStreak } from './streak';

/**
 * Reading seals: marks of a reading life, pressed as the reader reaches them.
 *
 * Every seal is WORKED OUT from what the device already keeps — finished stamps
 * on reading positions (synced with the account), the reading-day log behind
 * the streak, plan progress and the reader's own marks — the way the streak
 * and "Your year in books" are. Nothing new is stored, so a seal appears on a
 * new device the moment the account's progress arrives, and there is nothing
 * to take away: un-finishing a book only un-earns a seal until it is finished
 * again.
 *
 * The rules that keep them devotional rather than a game (founder-approved,
 * 2026-10): earned only by reading; never lost (a broken streak keeps its
 * seal — the seal is for the run first reached); private; and each one points
 * onward to something to read. Pure: every input is a parameter, so it is
 * tested without a browser.
 */

export type SealId =
	| 'first'
	| 'five'
	| 'year'
	| 'hearer'
	| 'pupil'
	| 'pilgrim'
	| 'margins'
	| 'week'
	| 'thirty'
	| 'hundred'
	| 'centuries'
	| 'tongues';

export type SealFamily = 'finishing' | 'depth' | 'faithfulness' | 'breadth';
export type SealState = 'earned' | 'progress' | 'locked';

export interface Seal {
	/** Unique per seal held: `pupil:<author>` for each writer's own. */
	key: string;
	id: SealId;
	family: SealFamily;
	state: SealState;
	have: number;
	need: number;
	/** When it was earned, as a local 'YYYY-MM-DD'; null when not earned or unknown. */
	earnedOn: string | null;
	/** The book (or plan) whose finishing earned it, when one did. */
	via: { kind: 'book' | 'sermon' | 'plan'; slug: string } | null;
	/** The writer of a Pupil seal. */
	author?: { slug: string; name: string };
	/** Through the Centuries: the eras still to read. */
	missingEras?: EraId[];
}

export const SEAL_FAMILY: Record<SealId, SealFamily> = {
	first: 'finishing',
	five: 'finishing',
	year: 'finishing',
	hearer: 'finishing',
	pupil: 'depth',
	pilgrim: 'depth',
	margins: 'depth',
	week: 'faithfulness',
	thirty: 'faithfulness',
	hundred: 'faithfulness',
	centuries: 'breadth',
	tongues: 'breadth'
};

/** Display order: the catalogue reads family by family. */
export const SEAL_ORDER: SealId[] = Object.keys(SEAL_FAMILY) as SealId[];

export interface SealInput {
	/** Every reading position, books and sermons, finished or not. */
	progress: { slug: string; kind: string; finished_at?: number | null; language?: string }[];
	/** The catalogue in the reader's language, for authors and their eras. */
	books: { slug: string; author: { slug: string; name: string; birth_year: number | null } }[];
	/** Days read, 'YYYY-MM-DD'. */
	days: Iterable<string>;
	/** Plans with their length, and the days the reader has marked done. */
	plans: { slug: string; day_count: number }[];
	planDone: Record<string, number[]>;
	/** How many highlights and notes the reader keeps. */
	marks: number;
}

const MARGINS = 25;
const PUPIL = 3;

/** A local calendar day from epoch ms. */
export const dayOf = (ms: number): string => {
	const d = new Date(ms);
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

/** The first day a run of consecutive reading days reached `n`, or null. */
export function firstRunReaching(days: Iterable<string>, n: number): string | null {
	const sorted = [...new Set(days)].sort();
	let run = 0;
	let prev: number | null = null;
	for (const d of sorted) {
		const t = Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10));
		run = prev !== null && t - prev === 86_400_000 ? run + 1 : 1;
		prev = t;
		if (run >= n) return d;
	}
	return null;
}

const seal = (id: SealId, have: number, need: number, rest: Partial<Seal> = {}): Seal => ({
	key: id,
	id,
	family: SEAL_FAMILY[id],
	state: have >= need ? 'earned' : have > 0 ? 'progress' : 'locked',
	have: Math.min(have, need),
	need,
	earnedOn: null,
	via: null,
	...rest
});

/** A count-of-finishes seal: earned on the `need`-th finish. */
function countSeal(
	id: SealId,
	finished: { slug: string; finished_at: number }[],
	need: number,
	kind: 'book' | 'sermon'
): Seal {
	const hit = finished[need - 1];
	return seal(id, finished.length, need, hit ? { earnedOn: dayOf(hit.finished_at), via: { kind, slug: hit.slug } } : {});
}

export function computeSeals(input: SealInput): Seal[] {
	const finished = (kind: string) =>
		input.progress
			.filter((p): p is typeof p & { finished_at: number } => p.kind === kind && p.finished_at != null)
			.sort((a, b) => a.finished_at - b.finished_at);
	const books = finished('book');
	const sermons = finished('sermon');
	const meta = new Map(input.books.map((b) => [b.slug, b]));
	const out: Seal[] = [];

	out.push(countSeal('first', books, 1, 'book'));
	out.push(countSeal('five', books, 5, 'book'));

	// A Book a Month: twelve finished within one calendar year. Earned in the
	// first year to reach twelve; until then, this year's count.
	const byYear = new Map<number, typeof books>();
	for (const b of books) {
		const y = new Date(b.finished_at).getFullYear();
		byYear.set(y, [...(byYear.get(y) ?? []), b]);
	}
	const fullYear = [...byYear.keys()].sort().find((y) => byYear.get(y)!.length >= 12);
	out.push(
		fullYear !== undefined
			? countSeal('year', byYear.get(fullYear)!, 12, 'book')
			: seal('year', byYear.get(new Date().getFullYear())?.length ?? 0, 12)
	);

	out.push(countSeal('hearer', sermons, 1, 'sermon'));

	// A Pupil seal for every writer the reader has finished three books by —
	// books this language's catalogue can name, as Year in Books counts them.
	const perAuthor = new Map<string, { name: string; done: typeof books }>();
	for (const b of books) {
		const a = meta.get(b.slug)?.author;
		if (!a) continue;
		const e = perAuthor.get(a.slug) ?? { name: a.name, done: [] };
		e.done.push(b);
		perAuthor.set(a.slug, e);
	}
	const pupils = [...perAuthor.entries()].filter(([, e]) => e.done.length >= PUPIL);
	if (pupils.length) {
		for (const [slug, e] of pupils) {
			const s = countSeal('pupil', e.done, PUPIL, 'book');
			out.push({ ...s, key: `pupil:${slug}`, author: { slug, name: e.name } });
		}
	} else {
		// On the way: the writer the reader has read most.
		const best = [...perAuthor.entries()].sort((a, b) => b[1].done.length - a[1].done.length)[0];
		out.push(
			best
				? { ...seal('pupil', best[1].done.length, PUPIL), author: { slug: best[0], name: best[1].name } }
				: seal('pupil', 0, PUPIL)
		);
	}

	// Pilgrim: a plan read to its last day.
	const walked = input.plans.find((p) => p.day_count > 0 && (input.planDone[p.slug]?.length ?? 0) >= p.day_count);
	const furthest = Math.max(
		0,
		...input.plans.map((p) => (p.day_count ? Math.min(1, (input.planDone[p.slug]?.length ?? 0) / p.day_count) : 0))
	);
	out.push(
		walked
			? seal('pilgrim', 1, 1, { via: { kind: 'plan', slug: walked.slug } })
			: { ...seal('pilgrim', 0, 1), state: furthest > 0 ? 'progress' : 'locked' }
	);

	out.push(seal('margins', input.marks, MARGINS));

	const days = [...input.days];
	const run = longestStreak(days);
	for (const [id, n] of [
		['week', 7],
		['thirty', 30],
		['hundred', 100]
	] as const) {
		out.push(seal(id, run, n, { earnedOn: firstRunReaching(days, n) }));
	}

	// Through the Centuries: a writer from every era, earned on the book that
	// completed the set.
	const seen = new Set<EraId>();
	let completedBy: (typeof books)[number] | null = null;
	for (const b of books) {
		const a = meta.get(b.slug)?.author;
		if (!a || a.birth_year == null) continue;
		seen.add(eraOf(a.birth_year));
		if (!completedBy && seen.size === ERAS.length) completedBy = b;
	}
	out.push(
		seal('centuries', seen.size, ERAS.length, {
			missingEras: ERAS.map((e) => e.id).filter((id) => !seen.has(id)),
			...(completedBy
				? { earnedOn: dayOf(completedBy.finished_at), via: { kind: 'book' as const, slug: completedBy.slug } }
				: {})
		})
	);

	// Two Tongues: finished works in two languages, earned on the first finish
	// in the second.
	const works = [
		...books.map((w) => ({ ...w, kind: 'book' as const })),
		...sermons.map((w) => ({ ...w, kind: 'sermon' as const }))
	].sort((a, b) => a.finished_at - b.finished_at);
	const langs = new Set<string>();
	let second: (typeof works)[number] | null = null;
	for (const w of works) {
		if (!w.language || langs.has(w.language)) continue;
		langs.add(w.language);
		if (langs.size === 2) second = w;
	}
	out.push(
		seal('tongues', langs.size, 2, second ? { earnedOn: dayOf(second.finished_at), via: { kind: second.kind, slug: second.slug } } : {})
	);

	return out;
}

/** Earned first (newest first), then on the way, then not yet — the shelf's order. */
export function shelfOrder(seals: Seal[]): Seal[] {
	const rank = { earned: 0, progress: 1, locked: 2 } as const;
	return [...seals].sort(
		(a, b) =>
			rank[a.state] - rank[b.state] ||
			(b.earnedOn ?? '').localeCompare(a.earnedOn ?? '') ||
			SEAL_ORDER.indexOf(a.id) - SEAL_ORDER.indexOf(b.id)
	);
}
