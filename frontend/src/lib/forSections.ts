import type { ForShelfData } from './forPages';

/**
 * The order an "Ochorus for …" page tells its story in. One template draws all
 * nine pages, and with one fixed order they read as nine copies of a page; but
 * a chaplain's first question is "can I take it where there is no signal?",
 * a parent's is "is there something my seven-year-old can read?", and a small
 * group leader's is "what do we read this term?". So each group LEADS with the
 * sections that answer it, and the rest follow in the default order. Order is
 * the reader's need, not the language's, so one table serves English and
 * French.
 *
 * Only the sections between the numbers strip and the closing band move; the
 * hero, the numbers and the closing band are the page's frame.
 */
export const FOR_SECTIONS = [
	'why',
	'quote',
	'plans',
	'series',
	'ideas',
	'shelves',
	'levels',
	'writers',
	'guides',
	'offline',
	'languages',
	'invite',
	'questions'
] as const;
export type ForSection = (typeof FOR_SECTIONS)[number];

/** Each group's leading sections, most useful first. A section the page
 *  doesn't have (French has no guides, offline pack or quotation) is skipped. */
export const FOR_LEAD: Record<string, ForSection[]> = {
	churches: ['plans', 'series', 'why', 'shelves', 'quote', 'guides'],
	'small-groups': ['series', 'plans', 'why', 'ideas', 'shelves'],
	youth: ['plans', 'shelves', 'why', 'ideas'],
	missionaries: ['offline', 'languages', 'why', 'shelves', 'plans'],
	chaplains: ['offline', 'why', 'shelves', 'plans'],
	'bible-colleges': ['shelves', 'why', 'writers', 'offline', 'plans'],
	schools: ['levels', 'guides', 'why', 'shelves', 'plans'],
	homeschool: ['levels', 'guides', 'plans', 'why', 'shelves'],
	parents: ['levels', 'plans', 'guides', 'why', 'shelves']
};

/** Does this page have anything to draw for the section? The copy-only
 *  sections (why, ideas, invite, questions) always do. */
export const hasSection = (s: ForSection, shelf: ForShelfData): boolean => {
	switch (s) {
		case 'quote':
			return !!shelf.quote;
		case 'plans':
		case 'series':
		case 'shelves':
		case 'levels':
		case 'guides':
		case 'offline':
		case 'languages':
			return shelf[s].length > 0;
		case 'writers':
			return shelf.authors.length > 0;
		default:
			return true;
	}
};

/** The page's sections in the order it shows them: its lead, then the rest
 *  in the default order, each only when it has something to draw. */
export function forSectionOrder(slug: string, shelf: ForShelfData): ForSection[] {
	const lead = FOR_LEAD[slug] ?? [];
	return [...lead, ...FOR_SECTIONS.filter((s) => !lead.includes(s))].filter((s) => hasSection(s, shelf));
}

/** The sections the jump bar lists: every one but the quotation, which has no
 *  heading of its own to land on. */
export const navSections = (order: ForSection[]): Exclude<ForSection, 'quote'>[] =>
	order.filter((s): s is Exclude<ForSection, 'quote'> => s !== 'quote');

/** The Plausible custom event the pages report their tools' use under, with
 *  `{ group, action }` props — short labels only ($lib/analytics). */
export const FOR_EVENT = 'For page';
