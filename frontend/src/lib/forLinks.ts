/**
 * The "Ochorus for …" pages' links — the footer's link to the hub, each page's
 * group switcher, the /for/ index and the share-card script. Kept apart from the page copy ($lib/forPages) because the
 * footer is in the layout: importing the copy there would ship every page's
 * text with every page. forPages.test.ts keeps the two lists in step.
 *
 * The pages exist in English and French (`FOR_LOCALES`): pitch copy is written
 * per language rather than through the catalogues, so each language is a
 * deliberate set of pages, not a placeholder. A reader in any other language
 * is not sent to them (the footer link is English and French only).
 */
export interface ForLinkDest {
	/** The URL segment: /for/<slug>/. */
	slug: string;
	/** The link text. */
	label: string;
	/** The link text in French. */
	fr: string;
	/** As it reads mid-sentence in the footer ("… for churches, small groups
	 *  and parents"): lower case but for proper nouns, and in French with its
	 *  article. */
	inline: string;
	frInline: string;
}

/** The languages the pages are written in. */
export const FOR_LOCALES = ['en', 'fr'] as const;
export type ForLocale = (typeof FOR_LOCALES)[number];

/** The page language for a UI locale: its own where the pages are written in
 *  it, else English (the pages' only copy a Swahili reader can be shown). */
export const forLocale = (locale: string): ForLocale =>
	(FOR_LOCALES as readonly string[]).includes(locale) ? (locale as ForLocale) : 'en';

/** In the order the /for/ index and the group switcher show them. */
export const FOR_LINKS: ForLinkDest[] = [
	{ slug: 'churches', label: 'Churches', fr: 'Églises', inline: 'churches', frInline: 'les Églises' },
	{ slug: 'pastors', label: 'Pastors', fr: 'Pasteurs', inline: 'pastors', frInline: 'les pasteurs' },
	{ slug: 'small-groups', label: 'Small groups', fr: 'Petits groupes', inline: 'small groups', frInline: 'les petits groupes' },
	{ slug: 'new-believers', label: 'New believers', fr: 'Nouveaux croyants', inline: 'new believers', frInline: 'les nouveaux croyants' },
	{ slug: 'evangelism', label: 'Evangelism', fr: 'Évangélisation', inline: 'evangelism', frInline: 'l’évangélisation' },
	{ slug: 'prayer-groups', label: 'Prayer groups', fr: 'Groupes de prière', inline: 'prayer groups', frInline: 'les groupes de prière' },
	{ slug: 'womens-ministry', label: 'Women’s ministry', fr: 'Femmes', inline: 'women’s ministry', frInline: 'les femmes' },
	{ slug: 'mens-ministry', label: 'Men’s ministry', fr: 'Hommes', inline: 'men’s ministry', frInline: 'les hommes' },
	{ slug: 'youth', label: 'Youth ministries', fr: 'Pastorale des jeunes', inline: 'youth ministries', frInline: 'la pastorale des jeunes' },
	{ slug: 'campus', label: 'Campus ministries', fr: 'Étudiants', inline: 'campus ministries', frInline: 'les étudiants' },
	{ slug: 'missionaries', label: 'Missionaries', fr: 'Missionnaires', inline: 'missionaries', frInline: 'les missionnaires' },
	{ slug: 'african-churches', label: 'African churches', fr: 'Églises d’Afrique', inline: 'African churches', frInline: 'les Églises d’Afrique' },
	{ slug: 'chaplains', label: 'Chaplains', fr: 'Aumôniers', inline: 'chaplains', frInline: 'les aumôniers' },
	{ slug: 'prison-ministry', label: 'Prison ministry', fr: 'Prisons', inline: 'prison ministry', frInline: 'les prisons' },
	{ slug: 'bible-colleges', label: 'Bible colleges', fr: 'Instituts bibliques', inline: 'Bible colleges', frInline: 'les instituts bibliques' },
	{ slug: 'schools', label: 'Schools', fr: 'Écoles', inline: 'schools', frInline: 'les écoles' },
	{ slug: 'homeschool', label: 'Homeschool families', fr: 'École à la maison', inline: 'homeschool families', frInline: 'l’école à la maison' },
	{ slug: 'parents', label: 'Parents', fr: 'Parents', inline: 'parents', frInline: 'les parents' }
];

/** A link's text in the page's language. */
export const forLabel = (l: ForLinkDest, locale: ForLocale): string => (locale === 'fr' ? l.fr : l.label);

/** A link's mid-sentence text in the page's language. */
export const forInline = (l: ForLinkDest, locale: ForLocale): string =>
	locale === 'fr' ? l.frInline : l.inline;

/** The row's name: "Ochorus for …" — the palette entries and each page's. */
export const FOR_EYEBROW: Record<ForLocale, string> = { en: 'Ochorus for', fr: 'Ochorus pour' };

/** The footer's one link to the /for/ hub, which lists every group page. Like
 *  the links, written per language rather than catalogued, and shown only to a
 *  reader of a language the pages are written in. */
export const FOR_FOOTER: Record<ForLocale, string> = {
	en: 'For churches & ministries',
	fr: 'Pour les Églises et les ministères'
};

/** The locale's path prefix: none for English. */
const prefix = (locale: ForLocale) => (locale === 'en' ? '' : `/${locale}`);

/** The index of every group page. */
export const FOR_INDEX = '/for/';

/** The index in a language, as it prerenders: slashed, locale-prefixed. */
export const forIndexPath = (locale: ForLocale = 'en') => `${prefix(locale)}${FOR_INDEX}`;

/** A page's path in a language — slashed, as it prerenders to
 *  [/<locale>]/for/<slug>/index.html. */
export const forPath = (slug: string, locale: ForLocale = 'en') => `${prefix(locale)}/for/${slug}/`;
