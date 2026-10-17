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
	},
	pastors: {
		accent: '#8a3f4f',
		emblem: 'shepherds-crook', // feed the flock of God which is among you
		phrase: 'pastors and preachers',
		tagline: 'The great preachers on preaching, prayer and the care of souls',
		fr: {
			phrase: 'les pasteurs et les prédicateurs',
			tagline: 'Les grands prédicateurs sur la prédication, la prière et le soin des âmes'
		}
	},
	'new-believers': {
		accent: '#4f86b8',
		emblem: 'open-gate', // I am the door
		phrase: 'new believers',
		tagline: 'Clear, warm first books and short plans for the first months of faith',
		fr: {
			phrase: 'les nouveaux croyants',
			tagline: 'Des premiers livres clairs et chaleureux pour les premiers mois de la foi'
		}
	},
	'prison-ministry': {
		accent: '#55606e',
		emblem: 'dove-at-the-bars', // to proclaim liberty to the captives
		phrase: 'prison ministry',
		tagline: 'Books of hope from those who wrote behind bars, free to print and pass on',
		fr: {
			phrase: 'l’aumônerie de prison',
			tagline: 'Des livres d’espérance écrits derrière les barreaux, à lire et à transmettre'
		}
	},
	'womens-ministry': {
		accent: '#a8457e',
		emblem: 'lamp-and-distaff', // her lamp does not go out by night
		phrase: 'women’s ministry',
		tagline: 'The lives and writings of women of faith, with plans to read together',
		fr: {
			phrase: 'les groupes de femmes',
			tagline: 'Les vies et les écrits de femmes de foi, à lire ensemble'
		}
	},
	'mens-ministry': {
		accent: '#3e6a8a',
		emblem: 'iron-sharpens-iron', // as iron sharpens iron
		phrase: 'men’s ministry',
		tagline: 'Lives of courage and books on prayer and holiness for men',
		fr: {
			phrase: 'les groupes d’hommes',
			tagline: 'Des vies de courage et des livres sur la prière et la sainteté'
		}
	},
	'prayer-groups': {
		accent: '#7451a8',
		emblem: 'golden-censer', // let my prayer be set forth as incense
		phrase: 'prayer groups',
		tagline: 'The great books on prayer and the stories of answered prayer',
		fr: {
			phrase: 'les groupes de prière',
			tagline: 'Les grands livres sur la prière et les récits de prières exaucées'
		}
	},
	evangelism: {
		accent: '#3d8a5a',
		emblem: 'sower-and-seed', // a sower went forth to sow
		phrase: 'evangelism and outreach',
		tagline: 'Gospel books to give away, and the classics on reaching others',
		fr: {
			phrase: 'l’évangélisation',
			tagline: 'Des livres d’Évangile à offrir, et les classiques de l’évangélisation'
		}
	},
	'african-churches': {
		accent: '#c0632a',
		emblem: 'baobab-at-dawn', // Ethiopia shall stretch out her hands unto God
		phrase: 'African churches',
		tagline: 'Africa’s church fathers, the East African Revival, and books in Swahili and Luganda',
		fr: {
			phrase: 'les Églises d’Afrique',
			tagline: 'Les Pères africains, le réveil d’Afrique de l’Est et des livres en swahili et en luganda'
		}
	},
	campus: {
		accent: '#36598f',
		emblem: 'college-tower', // the fear of the Lord is the beginning of wisdom
		phrase: 'campus ministries',
		tagline: 'Faith and reason, and the students who changed the world',
		fr: {
			phrase: 'les étudiants',
			tagline: 'Foi et raison, et les étudiants qui ont changé le monde'
		}
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
