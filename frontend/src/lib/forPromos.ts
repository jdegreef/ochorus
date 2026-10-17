import { FOR_LOCALES, type ForLocale } from './forLinks';
import type { ForSection } from './forSections';

/**
 * Where the rest of the site points a leader at the "Ochorus for …" pages, and
 * which page each place points to. The pages were reachable from the footer
 * alone; a leader meets Ochorus on a plan, a sermon or a hub, so each of those
 * now says, in one quiet line, "doing this with a group? — here is the page for
 * you". One table, so a new group page is wired in by editing it, and
 * forPromos.test.ts holds every slug and section to the pages that exist.
 *
 * The pages are written in English and French only ($lib/forLinks), so a line
 * shows only to readers in those two languages, as the footer row does.
 */
export const FOR_PLACES = [
	'plan',
	'plan-done',
	'plans-shelf',
	'sermon',
	'sermons-shelf',
	'young-readers',
	'teens',
	'guide',
	'book-download',
	'topic',
	'search'
] as const;
export type ForPlace = (typeof FOR_PLACES)[number];

/** A place's link: the groups it names, in order, and the section to land on. */
export interface ForPromo {
	slugs: string[];
	section?: ForSection;
}

export const FOR_PROMOS: Record<Exclude<ForPlace, 'topic' | 'search'>, ForPromo> = {
	plan: { slugs: ['small-groups', 'churches'], section: 'plans' },
	'plan-done': { slugs: ['small-groups'], section: 'plans' },
	'plans-shelf': { slugs: ['small-groups', 'churches', 'youth'], section: 'plans' },
	sermon: { slugs: ['small-groups'], section: 'series' },
	'sermons-shelf': { slugs: ['small-groups', 'churches'], section: 'series' },
	'young-readers': { slugs: ['parents', 'homeschool', 'schools'], section: 'levels' },
	teens: { slugs: ['youth', 'parents'] },
	guide: { slugs: ['schools', 'homeschool'], section: 'guides' },
	'book-download': { slugs: ['missionaries', 'chaplains'], section: 'offline' }
};

/** A topic shelf whose readers are often leading others, and their page. */
export const TOPIC_FOR: Record<string, string> = {
	'for-those-who-lead': 'churches',
	'grace-and-comfort': 'chaplains',
	'revival-and-missions': 'missionaries',
	'to-the-ends-of-the-earth': 'missionaries',
	'the-east-african-revival': 'missionaries',
	'for-young-readers': 'parents',
	'for-teens': 'youth',
	prayer: 'small-groups',
	'voices-of-the-early-church': 'bible-colleges',
	'the-puritans': 'bible-colleges',
	'foundations-of-the-faith': 'churches'
};

/** Words in a search that name a group, and its page. Whole words, lower case. */
export const SEARCH_FOR: Record<string, string> = {
	church: 'churches',
	churches: 'churches',
	congregation: 'churches',
	'small group': 'small-groups',
	'small groups': 'small-groups',
	'bible study': 'small-groups',
	youth: 'youth',
	teens: 'youth',
	teenagers: 'youth',
	missionary: 'missionaries',
	missionaries: 'missionaries',
	missions: 'missionaries',
	chaplain: 'chaplains',
	chaplains: 'chaplains',
	hospital: 'chaplains',
	prison: 'chaplains',
	'bible college': 'bible-colleges',
	seminary: 'bible-colleges',
	school: 'schools',
	schools: 'schools',
	classroom: 'schools',
	homeschool: 'homeschool',
	homeschooling: 'homeschool',
	parents: 'parents',
	children: 'parents',
	kids: 'parents'
};

/** The group page a search names, if any: the longest phrase it contains. */
export function searchFor(query: string): string | null {
	const q = ` ${query.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim()} `;
	const hit = Object.keys(SEARCH_FOR)
		.filter((k) => q.includes(` ${k} `))
		.sort((a, b) => b.length - a.length)[0];
	return hit ? SEARCH_FOR[hit] : null;
}

/** The page language a promo shows in, or null where the pages aren't written. */
export const promoLocale = (lang: string): ForLocale | null =>
	(FOR_LOCALES as readonly string[]).includes(lang) ? (lang as ForLocale) : null;

/** Each place's opening question, in each page language. */
export const PROMO_LEAD: Record<ForLocale, Record<ForPlace, string>> = {
	en: {
		plan: 'Reading this with a group?',
		'plan-done': 'Read the next one with others:',
		'plans-shelf': 'Reading with a group?',
		sermon: 'Discussing this sermon with a group?',
		'sermons-shelf': 'Leading a study?',
		'young-readers': 'Teaching children?',
		teens: 'Leading young people?',
		guide: 'Using this guide with a class?',
		'book-download': 'Taking books where there’s no signal?',
		topic: 'Leading others through this?',
		search: 'Looking for help as a leader?'
	},
	fr: {
		plan: 'Vous lisez ce plan en groupe ?',
		'plan-done': 'Lisez le suivant avec d’autres :',
		'plans-shelf': 'Vous lisez en groupe ?',
		sermon: 'Vous étudiez ce sermon en groupe ?',
		'sermons-shelf': 'Vous animez une étude ?',
		'young-readers': 'Vous enseignez aux enfants ?',
		teens: 'Vous accompagnez des jeunes ?',
		guide: 'Vous utilisez ce guide en classe ?',
		'book-download': 'Des livres à emporter là où il n’y a pas de réseau ?',
		topic: 'Vous accompagnez d’autres sur ce thème ?',
		search: 'Vous cherchez de l’aide pour votre groupe ?'
	}
};

/** "See" before the page names, and the index link's words. */
export const PROMO_WORDS: Record<ForLocale, { see: string; or: string; all: string; allLead: string }> = {
	en: { see: 'See', or: 'or', all: 'See who Ochorus is for', allLead: 'Leading a church, school or ministry?' },
	fr: {
		see: 'Voir',
		or: 'ou',
		all: 'Voir pour qui est Ochorus',
		allLead: 'Vous dirigez une Église, une école ou un ministère ?'
	}
};
