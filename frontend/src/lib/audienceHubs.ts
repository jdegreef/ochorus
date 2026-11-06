import type { IconName } from '$lib/components/Icon.svelte';
import type { HubAudience } from './library-public';

// The hub CONFIG alone: pure data with no runtime imports, split out of
// $lib/audienceHub so the nav and footer lists (contentNav, on every page)
// can name the hubs without pulling that module's helpers, and through them
// library-public and seo, into the JavaScript every page loads first.
// $lib/audienceHub re-exports all of it, so its importers are unchanged.

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
	hooks: false
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
	hooks: true
};

export const AUDIENCE_HUBS: AudienceHubConfig[] = [YOUNG_READERS_HUB, TEENS_HUB];
