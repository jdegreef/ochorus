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

export interface ForMeta {
	accent: string;
	/** Unique across every catalogue (emblems.test.ts). */
	emblem: EmblemName;
	/** "Ochorus for {phrase}": lower case, but "Bible" stays a proper noun. */
	phrase: string;
	tagline: string;
}

export const FOR_META: Record<string, ForMeta> = {
	churches: {
		accent: '#b0603a',
		emblem: 'village-church', // the church on the hill
		phrase: 'churches',
		tagline: 'A free library of the classics for your whole congregation'
	},
	'small-groups': {
		accent: '#2a8a7a',
		emblem: 'kindred-flames', // where two or three are gathered
		phrase: 'small groups',
		tagline: 'One book everyone can read, free, on their own phone'
	},
	youth: {
		accent: '#d4682a',
		emblem: 'summit-flag', // the climb ahead of them
		phrase: 'youth ministries',
		tagline: 'Classics retold, true stories and thirty-day devotionals for teens'
	},
	missionaries: {
		accent: '#2f6fa8',
		emblem: 'globe-and-book', // the Word carried to the nations
		phrase: 'missionaries',
		tagline: 'Classics to share in the languages you serve, online or off'
	},
	chaplains: {
		accent: '#4a5a95',
		emblem: 'lamp-in-window', // a light kept in the night
		phrase: 'chaplains',
		tagline: 'Comfort for the ward, the cell and the long night'
	},
	'bible-colleges': {
		accent: '#6a4a8f',
		emblem: 'scroll-and-quill', // the sources themselves
		phrase: 'Bible colleges',
		tagline: 'The church fathers, Reformers and Puritans, free for every student'
	},
	schools: {
		accent: '#3f8f4f',
		emblem: 'slate-and-apple', // the classroom
		phrase: 'schools',
		tagline: 'Primary sources and literature for every reading level'
	},
	homeschool: {
		accent: '#b8862e',
		emblem: 'lit-cottage', // the lamp in the kitchen window
		phrase: 'homeschool families',
		tagline: 'Living books for every age, with printable leader’s guides'
	},
	parents: {
		accent: '#c25a7a',
		emblem: 'sheltered-nest', // as a hen gathers her chicks
		phrase: 'parents',
		tagline: 'True stories, classic tales and five-minute family devotions'
	}
};

/** The /for/ index's title and its share card's words. */
export const FOR_INDEX_CARD = {
	eyebrow: 'The whole library, free',
	title: 'Who Ochorus is for',
	tagline: 'Free Christian classics for churches, groups, schools and families'
};
