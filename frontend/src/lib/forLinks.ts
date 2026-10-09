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
	/** One line under the label — the /for/ index card and the share card
	 *  (scripts/generate-for-og.mjs, which is why it lives here and not with
	 *  the page copy: this module imports nothing, so plain Node can read it). */
	tagline: string;
}

/** Left to right, as the footer row shows them. */
export const FOR_LINKS: ForLinkDest[] = [
	{ slug: 'churches', label: 'Churches', tagline: 'A free library of the classics for your whole congregation' },
	{ slug: 'small-groups', label: 'Small groups', tagline: 'One book everyone can read, free, on their own phone' },
	{ slug: 'youth', label: 'Youth ministries', tagline: 'Classics retold, true stories and thirty-day devotionals for teens' },
	{ slug: 'missionaries', label: 'Missionaries', tagline: 'Classics to share in the languages you serve, online or off' },
	{ slug: 'chaplains', label: 'Chaplains', tagline: 'Comfort for the ward, the cell and the long night' },
	{ slug: 'bible-colleges', label: 'Bible colleges', tagline: 'The church fathers, Reformers and Puritans, free for every student' },
	{ slug: 'schools', label: 'Schools', tagline: 'Primary sources and literature for every reading level' },
	{ slug: 'homeschool', label: 'Homeschool families', tagline: 'Living books for every age, with printable leader’s guides' },
	{ slug: 'parents', label: 'Parents', tagline: 'True stories, classic tales and five-minute family devotions' }
];

/** The index of every group page. */
export const FOR_INDEX = '/for/';

/** The index's share card (scripts/generate-for-og.mjs). */
export const FOR_INDEX_CARD = {
	eyebrow: 'The whole library, free',
	title: 'Who Ochorus is for',
	tagline: 'Free Christian classics for churches, groups, schools and families'
};

/** A label as it reads mid-sentence ("Ochorus for youth ministries"): lower
 *  case, except "Bible", which is a proper noun wherever it stands. */
export const forPhrase = (label: string) => label.toLowerCase().replace(/\bbible\b/g, 'Bible');

/** A page's canonical, unlocalized path — slashed, as it prerenders to
 *  /for/<slug>/index.html. English-only, so never locale-prefixed. */
export const forPath = (slug: string) => `/for/${slug}/`;
