import type { ForLocale } from './forLinks';
import type { ForSection } from './forSections';

/**
 * The /for/ index's two questions — who are you reading with, and what do you
 * want to do — answered with one link: the right group's page, landed on the
 * section that does that thing. Nine cards of equal weight make a visitor do
 * the sorting; two taps do it for them.
 *
 * A static table rather than the pages' own config, so the index doesn't ship
 * every page's copy to answer two questions; forPicker.test.ts holds it to the
 * pages, so a goal is offered only where its section is configured.
 */
export const FOR_GOALS = ['together', 'series', 'young', 'guides', 'offline', 'languages', 'books'] as const;
export type ForGoal = (typeof FOR_GOALS)[number];

/** The page section each goal lands on. */
export const GOAL_SECTION: Record<ForGoal, ForSection> = {
	together: 'plans',
	series: 'series',
	young: 'levels',
	guides: 'guides',
	offline: 'offline',
	languages: 'languages',
	books: 'shelves'
};

/** Each group's goals in each page language, most likely first. */
export const PICKER_GOALS: Record<string, Record<ForLocale, ForGoal[]>> = {
	churches: {
		en: ['together', 'series', 'guides', 'books'],
		fr: ['together', 'series', 'books']
	},
	'small-groups': {
		en: ['series', 'together', 'books'],
		fr: ['series', 'together', 'books']
	},
	youth: { en: ['together', 'books'], fr: ['together', 'books'] },
	missionaries: {
		en: ['offline', 'languages', 'together', 'books'],
		fr: ['languages', 'together', 'books']
	},
	chaplains: {
		en: ['offline', 'together', 'books'],
		fr: ['together', 'books']
	},
	'bible-colleges': {
		en: ['books', 'offline', 'together'],
		fr: ['books', 'together']
	},
	schools: {
		en: ['young', 'guides', 'together', 'books'],
		fr: ['young', 'together', 'books']
	},
	homeschool: {
		en: ['young', 'guides', 'together', 'books'],
		fr: ['young', 'together', 'books']
	},
	parents: {
		en: ['young', 'together', 'guides', 'books'],
		fr: ['young', 'together', 'books']
	},
	pastors: { en: ['books', 'series', 'together'], fr: ['books', 'series', 'together'] },
	'new-believers': { en: ['together', 'books', 'series'], fr: ['series', 'books', 'together'] },
	'prison-ministry': { en: ['offline', 'series', 'books', 'together'], fr: ['series', 'books', 'together'] },
	'prayer-groups': { en: ['together', 'series', 'books'], fr: ['together', 'series', 'books'] },
	'womens-ministry': { en: ['together', 'series', 'books'], fr: ['books', 'together'] },
	'mens-ministry': { en: ['together', 'series', 'books'], fr: ['books', 'series', 'together'] },
	evangelism: { en: ['books', 'offline', 'series', 'together'], fr: ['books', 'series', 'together'] },
	'african-churches': { en: ['languages', 'books', 'together'], fr: ['languages', 'books', 'together'] },
	campus: { en: ['books', 'together', 'series'], fr: ['books', 'series', 'together'] }
};

/** Where a choice leads: the group's page, at the goal's section. */
export const pickerHref = (pagePath: string, goal: ForGoal): string => `${pagePath}#${GOAL_SECTION[goal]}`;
