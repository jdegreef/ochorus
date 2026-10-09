/**
 * The "Ochorus for …" pages' links — the footer's bottom row and each page's
 * "also for" line. Kept apart from the page copy ($lib/forPages) because the
 * footer is in the layout: importing the copy there would ship every page's
 * text with every page. forPages.test.ts keeps the two lists in step.
 */
export interface ForLinkDest {
	/** The URL segment: /for/<slug>/. */
	slug: string;
	/** The link text. */
	label: string;
}

/** Left to right, as the footer row shows them. */
export const FOR_LINKS: ForLinkDest[] = [
	{ slug: 'churches', label: 'Churches' },
	{ slug: 'small-groups', label: 'Small groups' },
	{ slug: 'youth', label: 'Youth ministries' },
	{ slug: 'missionaries', label: 'Missionaries' },
	{ slug: 'chaplains', label: 'Chaplains' },
	{ slug: 'bible-colleges', label: 'Bible colleges' },
	{ slug: 'schools', label: 'Schools' },
	{ slug: 'homeschool', label: 'Homeschool families' },
	{ slug: 'parents', label: 'Parents' }
];

/** The index of every group page. */
export const FOR_INDEX = '/for/';

/** A page's canonical, unlocalized path — slashed, as it prerenders to
 *  /for/<slug>/index.html. English-only, so never locale-prefixed. */
export const forPath = (slug: string) => `/for/${slug}/`;
