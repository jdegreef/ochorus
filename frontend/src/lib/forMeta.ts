/**
 * Each "Ochorus for …" group's identity beyond its footer link ($lib/forLinks):
 * the accent and emblem its page, its /for/ index card and its share card wear,
 * the label as it reads mid-sentence, and the one line under it on the index
 * and the share card.
 *
 * A module of its own for two readers that cannot afford more: the root layout
 * imports `$lib/forLinks` for the footer, so none of this rides there; and
 * `scripts/generate-for-og.mjs` reads it under plain Node, so it imports
 * nothing but a type (stripped). One key per FOR_LINKS slug (forCards.test.ts).
 *
 * hex-ok-file: the curated accents are catalogue identity, like TOPIC_META's.
 */
import type { EmblemName } from './emblems';
import type { ForLocale } from './forLinks';

export interface ForMeta {
	accent: string;
	/** Unique across every catalogue (emblems.test.ts). */
	emblem: EmblemName;
	/** "Ochorus for {phrase}": lower case, but "Bible" stays a proper noun. */
	phrase: string;
	tagline: string;
	/** The phrase ("Ochorus pour {phrase}") and tagline in French, true of the
	 *  French library (no leader's guides there yet). */
	fr: { phrase: string; tagline: string };
}

export const FOR_META: Record<string, ForMeta> = {
	churches: {
		accent: '#b0603a',
		emblem: 'village-church', // the church on the hill
		phrase: 'churches',
		tagline: 'A free library of the classics for your whole congregation',
		fr: { phrase: 'les Églises', tagline: 'Une bibliothèque gratuite de classiques pour toute votre Église' }
	},
	'small-groups': {
		accent: '#2a8a7a',
		emblem: 'kindred-flames', // where two or three are gathered
		phrase: 'small groups',
		tagline: 'One book everyone can read, free, on their own phone',
		fr: { phrase: 'les petits groupes', tagline: 'Un livre que chacun peut lire, gratuit, sur son téléphone' }
	},
	youth: {
		accent: '#d4682a',
		emblem: 'summit-flag', // the climb ahead of them
		phrase: 'youth ministries',
		tagline: 'Classics retold, true stories and thirty-day devotionals for teens',
		fr: { phrase: 'la pastorale des jeunes', tagline: 'Classiques racontés, histoires vraies et méditations pour ados' }
	},
	missionaries: {
		accent: '#2f6fa8',
		emblem: 'globe-and-book', // the Word carried to the nations
		phrase: 'missionaries',
		tagline: 'Classics to share in the languages you serve, online or off',
		fr: { phrase: 'les missionnaires', tagline: 'Des classiques à partager dans les langues que vous servez' }
	},
	chaplains: {
		accent: '#4a5a95',
		emblem: 'lamp-in-window', // a light kept in the night
		phrase: 'chaplains',
		tagline: 'Comfort for the ward, the cell and the long night',
		fr: { phrase: 'les aumôniers', tagline: 'Du réconfort pour la chambre, la cellule et la longue nuit' }
	},
	'bible-colleges': {
		accent: '#6a4a8f',
		emblem: 'scroll-and-quill', // the sources themselves
		phrase: 'Bible colleges',
		tagline: 'The church fathers, Reformers and Puritans, free for every student',
		fr: { phrase: 'les instituts bibliques', tagline: 'Les Pères, Pascal et les puritains, gratuits pour chaque étudiant' }
	},
	schools: {
		accent: '#3f8f4f',
		emblem: 'slate-and-apple', // the classroom
		phrase: 'schools',
		tagline: 'Primary sources and literature for every reading level',
		fr: { phrase: 'les écoles', tagline: 'Sources et littérature pour chaque niveau de lecture' }
	},
	homeschool: {
		accent: '#b8862e',
		emblem: 'lit-cottage', // the lamp in the kitchen window
		phrase: 'homeschool families',
		tagline: 'Living books for every age, with printable leader’s guides',
		fr: { phrase: 'l’école à la maison', tagline: 'Des livres vivants pour tous les âges, et des dévotions familiales' }
	},
	parents: {
		accent: '#c25a7a',
		emblem: 'sheltered-nest', // as a hen gathers her chicks
		phrase: 'parents',
		tagline: 'True stories, classic tales and five-minute family devotions',
		fr: { phrase: 'les parents', tagline: 'Histoires vraies, récits classiques et dévotions de cinq minutes' }
	}
};

/** The /for/ index's title and its share card's words. */
export const FOR_INDEX_CARD = {
	eyebrow: 'The whole library, free',
	title: 'Who Ochorus is for',
	tagline: 'Free Christian classics for churches, groups, schools and families'
};

/** The same in French. */
export const FOR_INDEX_CARD_FR: typeof FOR_INDEX_CARD = {
	eyebrow: 'Toute la bibliothèque, gratuite',
	title: 'Pour qui est Ochorus',
	tagline: 'Classiques chrétiens gratuits pour Églises, groupes, écoles et familles'
};

/** A group's phrase, its tagline and the index card, in the page's language. */
export const forPhrase = (slug: string, locale: ForLocale): string =>
	locale === 'fr' ? FOR_META[slug].fr.phrase : FOR_META[slug].phrase;
export const forTagline = (slug: string, locale: ForLocale): string =>
	locale === 'fr' ? FOR_META[slug].fr.tagline : FOR_META[slug].tagline;
export const forIndexCard = (locale: ForLocale): typeof FOR_INDEX_CARD =>
	locale === 'fr' ? FOR_INDEX_CARD_FR : FOR_INDEX_CARD;
