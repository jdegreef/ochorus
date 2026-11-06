import { editionKind } from './edition';
import {
	toBookTile,
	type AudienceShelf,
	type BookSummary,
	type BookTile,
	type EditionRung
} from './library-public';
import { furthestOf, resumeOrderOf, type ProgressRecord } from './reading-schema';

import { AUDIENCE_HUBS, type AudienceHubConfig, type HubPathConfig } from './audienceHubs';
export {
	AUDIENCE_HUBS,
	YOUNG_READERS_HUB,
	TEENS_HUB,
	type AudienceHubConfig,
	type HubPathConfig
} from './audienceHubs';

/** The Plausible event a hub sends when its "Start here", a path card, a
 *  face, its challenge, spotlight or a ladder step is opened, or it is shared —
 *  props `{ hub, action }` (`start`, `path`, `person`, `challenge`,
 *  `spotlight`, `ladder`, `spotlight-share`, `challenge-share`, `share`); its
 *  visits are the pageviews themselves. */
export const HUB_EVENT = 'Hub';

/** The hub for a series audience, if it has one (adults don't). */
export const hubFor = (audience: string | null | undefined): AudienceHubConfig | undefined =>
	AUDIENCE_HUBS.find((h) => h.audience === audience);

/** Every book card the hub shows (series volumes are tiles, not cards). */
export function hubBooks(shelf: AudienceShelf): BookSummary[] {
	return [...shelf.editions, ...shelf.more];
}

/** The "Start here" book — the API's pick (`AUDIENCE_STARTS`), as a card. */
export function startPick(shelf: AudienceShelf): BookSummary | null {
	return hubBooks(shelf).find((b) => b.slug === shelf.start) ?? null;
}

/** Books and series on the hub, for the header's counts line. */
export function hubCounts(shelf: AudienceShelf): { books: number; series: number } {
	const inSeries = shelf.series.reduce((n, s) => n + s.book_count, 0);
	return { books: inSeries + hubBooks(shelf).length, series: shelf.series.length };
}

/** Whether the hub has anything to show in this language. */
export function hubIsEmpty(shelf: AudienceShelf): boolean {
	return !shelf.series.length && !hubBooks(shelf).length;
}

export interface HubPath {
	titleKey: string;
	lineKey: string;
	/** Unlocalized. */
	href: string;
	/** The covers the card fans: what is behind it, at a glance. */
	covers: BookTile[];
}

/** The hub's path cards whose place it has in this language, resolved to a
 *  link and the covers behind it. */
export function hubPaths(hub: AudienceHubConfig, shelf: AudienceShelf): HubPath[] {
	const start = startPick(shelf);
	const place = (to: HubPathConfig['to']): Pick<HubPath, 'href' | 'covers'> | null => {
		if (to === 'start') {
			return start && { href: `/books/${start.slug}`, covers: [toBookTile(start)] };
		}
		if ('section' in to) {
			const covers = shelf.editions.map(toBookTile);
			return covers.length ? { href: `#${to.section}`, covers } : null;
		}
		const series = shelf.series.find((s) => s.slug === to.series);
		return series ? { href: `/series/${series.slug}/`, covers: series.covers } : null;
	};
	return hub.paths.flatMap(({ titleKey, lineKey, to }) => {
		const at = place(to);
		return at ? [{ titleKey, lineKey, ...at }] : [];
	});
}

/** The hero's fan: the start pick in front, flanked by the first volume of
 *  each series — what the hub is, in three covers. */
export function heroCovers(shelf: AudienceShelf): BookTile[] {
	const start = startPick(shelf);
	const firsts = shelf.series.flatMap((s) => s.covers.slice(0, 1));
	if (!start) return firsts.slice(0, 3);
	const [a, b] = firsts.filter((c) => c.slug !== start.slug);
	return [a, toBookTile(start), b].filter((t): t is BookTile => !!t);
}

/** Where a reader stands in a challenge series (`AudienceShelf.challenge`). */
export interface ChallengeState {
	/** The volume to read: the first one not finished (the last, when all are). */
	slug: string;
	/** Days reached in it, 0 before day 1. */
	day: number;
	/** The chapter to open: where the reader left off, or the introduction. */
	order: number;
	started: boolean;
	/** Every volume finished. */
	done: boolean;
}

/** The reader's place in a challenge series, from their progress records
 *  (`recordOf` — `getProgressRecord` on the page; a stub in tests). */
export function challengeState(
	volumes: string[],
	days: number,
	recordOf: (slug: string) => ProgressRecord | null
): ChallengeState | null {
	if (!volumes.length) return null;
	const open = volumes.find((slug) => recordOf(slug)?.finished_at == null);
	const done = !open;
	const slug = open ?? volumes[volumes.length - 1];
	const rec = recordOf(slug);
	// furthestOf is at least 1 (the introduction), so day is never negative.
	const day = done ? days : rec ? Math.min(furthestOf(rec) - 1, days) : 0;
	return { slug, day, order: rec ? resumeOrderOf(rec) : 1, started: !!rec, done };
}

/** A ladder rung's words: "For children", "For teens", "The original". */
export const RUNG_LABEL = {
	children: 'audience.rungChildren',
	teens: 'audience.rungTeens',
	full: 'audience.rungFull'
} as const satisfies Record<EditionRung['rung'], string>;

/** The ladder's order, youngest first — as `EditionLadder` and the API's
 *  `_edition_ladders` give it. */
const RUNG_ORDER = { children: 0, teens: 1, full: 2 } as const satisfies Record<EditionRung['rung'], number>;

/**
 * A work's editions — `current` and the API's `editions` of it — each with its
 * rung, youngest first. The full text is the family's base, the slug the
 * others extend (the shortest), so an ORIGINAL whose own slug ends in a suffix
 * (Watts's `divine-songs-for-children`) is still "The original" among its
 * retellings; the rest are named by their suffix (`editionKind`).
 */
export function editionFamily<T extends { slug: string }>(
	current: T,
	others: readonly T[]
): { book: T; rung: EditionRung['rung'] }[] {
	const all = [current, ...others];
	const base = all.reduce((a, b) => (b.slug.length < a.slug.length ? b : a)).slug;
	return all
		.map((book) => ({ book, rung: book.slug === base ? 'full' : (editionKind(book.slug) ?? 'full') }) as const)
		.sort((a, b) => RUNG_ORDER[a.rung] - RUNG_ORDER[b.rung]);
}

/** The step after `slug` on its edition ladder — what "Ready for more"
 *  offers a reader who has a retelling in hand — or null at the top. */
export function nextRung(ladder: EditionRung[] | undefined, slug: string): EditionRung | null {
	const at = ladder?.findIndex((r) => r.slug === slug) ?? -1;
	return at >= 0 ? (ladder![at + 1] ?? null) : null;
}

export interface PrintableLink {
	/** Unlocalized. */
	href: string;
	label: string;
}

/**
 * The printable books, for the parents' note: a series with any printable
 * volume is ONE link to its page (Brave for God's four PDFs are one tag, not
 * four), and a stand-alone printable book links to itself. Series first, in
 * the hub's order, then books.
 */
export function printableLinks(shelf: AudienceShelf): PrintableLink[] {
	const printable = new Set(shelf.printable);
	const series = shelf.series
		.filter((s) => (s.books ?? []).some((slug) => printable.has(slug)))
		.map((s) => ({ href: `/series/${s.slug}/`, label: s.title }));
	const books = hubBooks(shelf)
		.filter((b) => printable.has(b.slug))
		.map((b) => ({ href: `/books/${b.slug}`, label: b.title }));
	return [...series, ...books];
}
