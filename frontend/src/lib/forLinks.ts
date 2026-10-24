/**
 * The "Ochorus for …" pages' links — the footer's closing sentence, each page's
 * group switcher, the /for/ index and the share-card script. Kept apart from the page copy ($lib/forPages) because the
 * footer is in the layout: importing the copy there would ship every page's
 * text with every page. forPages.test.ts keeps the two lists in step.
 *
 * The pages exist in English and French (`FOR_LOCALES`): pitch copy is written
 * per language rather than through the catalogues, so each language is a
 * deliberate set of pages, not a placeholder. A reader in any other language
 * is not sent to them (the footer row is English and French only).
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
	/** The footer column it sits in (FOR_FAMILIES). */
	family: ForFamily;
}

/** The footer's four columns, left to right: who a page is for, grouped so
 *  eighteen links read as four short lists rather than one long sentence. */
export const FOR_FAMILIES = [
	{ id: 'church', en: 'Church', fr: 'Église' },
	{ id: 'mission', en: 'Mission', fr: 'Mission' },
	{ id: 'learning', en: 'Learning', fr: 'Formation' },
	{ id: 'home', en: 'Home', fr: 'Foyer' }
] as const;
export type ForFamily = (typeof FOR_FAMILIES)[number]['id'];

/** The languages the pages are written in. */
export const FOR_LOCALES = ['en', 'fr'] as const;
export type ForLocale = (typeof FOR_LOCALES)[number];

/** The page language for a UI locale: its own where the pages are written in
 *  it, else English (the pages' only copy a Swahili reader can be shown). */
export const forLocale = (locale: string): ForLocale =>
	(FOR_LOCALES as readonly string[]).includes(locale) ? (locale as ForLocale) : 'en';

/** Left to right, as the footer row shows them. */
export const FOR_LINKS: ForLinkDest[] = [
	{ slug: 'churches', family: 'church', label: 'Churches', fr: 'Églises', inline: 'churches', frInline: 'les Églises' },
	{ slug: 'pastors', family: 'church', label: 'Pastors', fr: 'Pasteurs', inline: 'pastors', frInline: 'les pasteurs' },
	{ slug: 'small-groups', family: 'church', label: 'Small groups', fr: 'Petits groupes', inline: 'small groups', frInline: 'les petits groupes' },
	{ slug: 'new-believers', family: 'home', label: 'New believers', fr: 'Nouveaux croyants', inline: 'new believers', frInline: 'les nouveaux croyants' },
	{ slug: 'evangelism', family: 'mission', label: 'Evangelism', fr: 'Évangélisation', inline: 'evangelism', frInline: 'l’évangélisation' },
	{ slug: 'prayer-groups', family: 'church', label: 'Prayer groups', fr: 'Groupes de prière', inline: 'prayer groups', frInline: 'les groupes de prière' },
	{ slug: 'womens-ministry', family: 'church', label: 'Women’s ministry', fr: 'Femmes', inline: 'women’s ministry', frInline: 'les femmes' },
	{ slug: 'mens-ministry', family: 'church', label: 'Men’s ministry', fr: 'Hommes', inline: 'men’s ministry', frInline: 'les hommes' },
	{ slug: 'youth', family: 'learning', label: 'Youth ministries', fr: 'Pastorale des jeunes', inline: 'youth ministries', frInline: 'la pastorale des jeunes' },
	{ slug: 'campus', family: 'learning', label: 'Campus ministries', fr: 'Étudiants', inline: 'campus ministries', frInline: 'les étudiants' },
	{ slug: 'missionaries', family: 'mission', label: 'Missionaries', fr: 'Missionnaires', inline: 'missionaries', frInline: 'les missionnaires' },
	{ slug: 'african-churches', family: 'mission', label: 'African churches', fr: 'Églises d’Afrique', inline: 'African churches', frInline: 'les Églises d’Afrique' },
	{ slug: 'chaplains', family: 'mission', label: 'Chaplains', fr: 'Aumôniers', inline: 'chaplains', frInline: 'les aumôniers' },
	{ slug: 'prison-ministry', family: 'mission', label: 'Prison ministry', fr: 'Prisons', inline: 'prison ministry', frInline: 'les prisons' },
	{ slug: 'bible-colleges', family: 'learning', label: 'Bible colleges', fr: 'Instituts bibliques', inline: 'Bible colleges', frInline: 'les instituts bibliques' },
	{ slug: 'schools', family: 'learning', label: 'Schools', fr: 'Écoles', inline: 'schools', frInline: 'les écoles' },
	{ slug: 'homeschool', family: 'home', label: 'Homeschool families', fr: 'École à la maison', inline: 'homeschool families', frInline: 'l’école à la maison' },
	{ slug: 'parents', family: 'home', label: 'Parents', fr: 'Parents', inline: 'parents', frInline: 'les parents' }
];

/** A link's text in the page's language. */
export const forLabel = (l: ForLinkDest, locale: ForLocale): string => (locale === 'fr' ? l.fr : l.label);

/** A link's mid-sentence text in the page's language. */
export const forInline = (l: ForLinkDest, locale: ForLocale): string =>
	locale === 'fr' ? l.frInline : l.inline;

/** A family's links, in FOR_LINKS order: one footer column. */
export const forFamilyLinks = (family: ForFamily): ForLinkDest[] => FOR_LINKS.filter((l) => l.family === family);

/** The row's name: "Ochorus for …" — the footer eyebrow and each page's. */
export const FOR_EYEBROW: Record<ForLocale, string> = { en: 'Ochorus for', fr: 'Ochorus pour' };

/** The footer row's own words, beside the links. Like the links, written per
 *  language rather than catalogued (the French library has no leader's guides
 *  yet, so its line doesn't promise them). */
export const FOR_FOOTER: Record<
	ForLocale,
	{ title: string; body: string; thisWeek: string; share: string; shareTitle: string; copied: string }
> = {
	en: {
		title: 'Bring the classics to your people.',
		body: 'Free books, reading plans and leader’s guides for every kind of ministry and home.',
		thisWeek: 'This week:',
		share: 'Pass it on to your pastor',
		shareTitle: 'Ochorus for pastors',
		copied: 'Link copied'
	},
	fr: {
		title: 'Apportez les classiques à ceux que vous servez.',
		body: 'Des livres et des parcours de lecture gratuits, pour chaque ministère et chaque foyer.',
		thisWeek: 'Cette semaine :',
		share: 'Faites-le connaître à votre pasteur',
		shareTitle: 'Ochorus pour les pasteurs',
		copied: 'Lien copié'
	}
};

/** The group the footer features this week: each in turn, changing on Monday
 *  (UTC), so every page view in a week shows the same one. */
export function forOfTheWeek(now: number = Date.now()): ForLinkDest {
	const MONDAY_1970 = Date.UTC(1970, 0, 5);
	const week = Math.floor((now - MONDAY_1970) / (7 * 86_400_000));
	return FOR_LINKS[week % FOR_LINKS.length];
}

/** The locale's path prefix: none for English. */
const prefix = (locale: ForLocale) => (locale === 'en' ? '' : `/${locale}`);

/** The index of every group page. */
export const FOR_INDEX = '/for/';

/** The index in a language, as it prerenders: slashed, locale-prefixed. */
export const forIndexPath = (locale: ForLocale = 'en') => `${prefix(locale)}${FOR_INDEX}`;

/** A page's path in a language — slashed, as it prerenders to
 *  [/<locale>]/for/<slug>/index.html. */
export const forPath = (slug: string, locale: ForLocale = 'en') => `${prefix(locale)}/for/${slug}/`;
