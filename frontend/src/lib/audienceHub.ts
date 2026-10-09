import { editionKind } from './edition';
import type { IconName } from '$lib/components/Icon.svelte';
import {
	toBookTile,
	type AudienceShelf,
	type BookSummary,
	type BookTile,
	type EditionRung,
	type HubAudience
} from './library-public';
import { furthestOf, resumeOrderOf, type ProgressRecord } from './reading-schema';

/**
 * The young-reader hubs — /young-readers/ and /teens/ — one front door each to
 * what /series, /originals, /topics and /plans each hold a part of. The page is
 * one component (`AudienceHub.svelte`) driven by this table; the data is one
 * call (`$lib/audienceHubData`), so a new retelling, series or plan for either
 * audience lands on its hub with no edit here. Pure data and helpers — the nav
 * lists import it — so the loaders live in that module, not this one.
 *
 * Two hubs, not one "Kids" page: the young-readers hub speaks to the adult who
 * chooses for a child, the teens hub to the teenager choosing for themselves —
 * which is why each carries its own copy keys rather than sharing one voice.
 */
/**
 * One "where do you want to start?" card: a feeling or a need, pointing at one
 * real place on the hub — a series page, a group further down, or the editor's
 * start pick. A path whose place this language doesn't have is left out
 * (`hubPaths`), so the cards never promise what the page can't open.
 */
export interface HubPathConfig {
	/** The question or the name ("Got big questions?", "Brave heroes"). */
	titleKey: string;
	/** One line on what's behind it. */
	lineKey: string;
	to: { series: string } | { section: 'retold' } | 'start';
}

export interface AudienceHubConfig {
	audience: HubAudience;
	/** Unlocalized, unslashed — `localizeHref` adds the slash (isSlashedPath).
	 *  With `labelKey`, the shape of a `HubDest`, so the nav lists take it as is. */
	href: string;
	/** The nav word: the `<h1>`, the `<title>`, and every link to the page. */
	labelKey: string;
	/** Its tile in the phone's More sheet. */
	icon: IconName;
	/** The page's tagline; the home page's card line too. */
	taglineKey: string;
	/** What a search result shows: the `<title>` and the meta description, in
	 *  the words people search with ("free Christian books for children"). */
	seoTitleKey: string;
	seoDescriptionKey: string;
	/** The share button's words — who the page is passed on to. */
	shareKey: string;
	/** The line over the "Start here" pick. */
	startKey: string;
	/** The note under "Classics, retold". */
	retoldKey: string;
	/** Who the closing note is for, and what it suggests they do. */
	parentsHeadingKey: string;
	parentsTogetherKey: string;
	/** The /series audience group's link here. */
	seeKey: string;
	/** The heading over the path cards, and the cards, in order. */
	pathsHeadingKey: string;
	paths: HubPathConfig[];
	/** The people strip's heading and the line under it. */
	peopleHeadingKey: string;
	peopleNoteKey: string;
	/** The note for the adults, folded shut: on a page the reader chose for
	 *  themselves, a note about them shouldn't sit open at the end. */
	foldParents: boolean;
	/** Each book card carries the book's one-line hook (`BookSummary.hook`),
	 *  where it has one: the teenager picks by the story, not the cover. */
	hooks: boolean;
	/** The hub's daily devotional series, framed as a challenge. */
	challenge: HubChallenge;
}

/**
 * A "30 Days with God" series as a challenge: Anchored for teens, Rooted for
 * young readers. Each volume is an introduction (chapter 1), then one chapter
 * a day (chapter n + 1 is day n) — the convention `tests_audience_shelf`
 * holds the fixture to — so a reader's furthest chapter is the day they've
 * reached, with no new data.
 */
export interface HubChallenge {
	series: string;
	days: number;
}

export const YOUNG_READERS_HUB: AudienceHubConfig = {
	audience: 'young_readers',
	href: '/young-readers',
	labelKey: 'nav.youngReaders',
	icon: 'sun',
	taglineKey: 'audience.youngTagline',
	seoTitleKey: 'audience.youngSeoTitle',
	seoDescriptionKey: 'audience.youngSeoDescription',
	shareKey: 'audience.shareYoung',
	startKey: 'audience.startYoung',
	retoldKey: 'audience.retoldYoung',
	parentsHeadingKey: 'series.parentsHeading',
	parentsTogetherKey: 'audience.parentsTogetherYoung',
	seeKey: 'audience.seeYoung',
	pathsHeadingKey: 'audience.pathsHeadingYoung',
	paths: [
		{ titleKey: 'audience.pathNew', lineKey: 'audience.startYoung', to: 'start' },
		{ titleKey: 'audience.pathBrave', lineKey: 'audience.pathBraveLine', to: { series: 'brave-for-god' } },
		{ titleKey: 'audience.pathBedtime', lineKey: 'audience.pathBedtimeLine', to: { section: 'retold' } },
		{ titleKey: 'audience.pathDaily', lineKey: 'audience.pathDailyLine', to: { series: 'rooted' } }
	],
	peopleHeadingKey: 'audience.peopleHeadingYoung',
	peopleNoteKey: 'audience.peopleNoteYoung',
	foldParents: false,
	hooks: false,
	challenge: { series: 'rooted', days: 30 }
};

export const TEENS_HUB: AudienceHubConfig = {
	audience: 'teens',
	href: '/teens',
	labelKey: 'nav.teens',
	icon: 'compass',
	taglineKey: 'audience.teensTagline',
	seoTitleKey: 'audience.teensSeoTitle',
	seoDescriptionKey: 'audience.teensSeoDescription',
	shareKey: 'audience.shareTeens',
	startKey: 'audience.startTeens',
	retoldKey: 'audience.retoldTeens',
	parentsHeadingKey: 'audience.parentsTeensHeading',
	parentsTogetherKey: 'audience.parentsTogetherTeens',
	seeKey: 'audience.seeTeens',
	pathsHeadingKey: 'audience.pathsHeadingTeens',
	paths: [
		{ titleKey: 'audience.pathPick', lineKey: 'audience.pathPickLine', to: 'start' },
		{ titleKey: 'audience.pathQuestions', lineKey: 'audience.pathQuestionsLine', to: { series: 'anchored' } },
		{ titleKey: 'audience.pathTrue', lineKey: 'audience.pathTrueLine', to: { series: 'they-were-young' } },
		{ titleKey: 'audience.pathAdventure', lineKey: 'audience.pathAdventureLine', to: { series: 'straight-talk' } }
	],
	peopleHeadingKey: 'audience.peopleHeadingTeens',
	peopleNoteKey: 'audience.peopleNoteTeens',
	foldParents: true,
	hooks: true,
	challenge: { series: 'anchored', days: 30 }
};

export const AUDIENCE_HUBS: AudienceHubConfig[] = [YOUNG_READERS_HUB, TEENS_HUB];

/** The Plausible event a hub sends when its "Start here", a path card, a
 *  face, its challenge, spotlight or a ladder step is opened, or it is shared —
 *  props `{ hub, action }` (`start`, `path`, `person`, `challenge`,
 *  `spotlight`, `ladder`, `share`); its visits are the pageviews themselves. */
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

/** Where a reader stands in a challenge series (`HubChallenge`). */
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

/** Which rung an edition is, read off its slug (`editionKind`). Only for a
 *  book the API has already placed in a family (`editions`): a full text whose
 *  own slug ends so is never offered one. */
export function rungOf(slug: string): EditionRung['rung'] {
	return editionKind(slug) ?? 'full';
}

/** A book page's order: the original first, where a reader most often arrives. */
const RUNG_ORDER = { full: 0, teens: 1, children: 2 } as const satisfies Record<EditionRung['rung'], number>;

/** A work's editions with `current` placed among the others (which the API
 *  sends already in this order). */
export function editionFamily<T extends { slug: string }>(current: T, others: readonly T[]): T[] {
	return [current, ...others].sort((a, b) => RUNG_ORDER[rungOf(a.slug)] - RUNG_ORDER[rungOf(b.slug)]);
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
