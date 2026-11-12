/**
 * Journey maps: an allegory drawn as a road, each place on it a stop linked to
 * the chapter where it happens (the book page's "The pilgrim's road").
 *
 * PER-BOOK CONFIG, deliberately small: a book gets a map by gaining an entry
 * here — The Holy War (Mansoul's siege) could be the next. Stops are placed on
 * a 720 × 360 canvas, in reading order; `chapter` is the chapter `order` in
 * which the reader reaches the place, read off the text, never guessed —
 * `evidence` is a phrase from that chapter that `journeyMaps.test.ts` finds in
 * the English fixture, so a re-chaptered book fails the build instead of
 * pointing a stop at the wrong chapter.
 *
 * The place names are the book's own English words, so a map is offered only
 * on the edition whose language it is written in (`language`). Chapter orders
 * match across a book's translations, but a Swahili page under English names
 * would be a half-translated page; a translated map is a new entry's job.
 */

export interface JourneyStop {
	name: string;
	/** The chapter (`order`) in which the reader reaches this place. */
	chapter: number;
	/** A phrase from that chapter's text — the test's proof of `chapter`. */
	evidence: string;
	x: number;
	y: number;
	/** Where the name sits relative to the stop (the canvas is tight). */
	label: 'above' | 'below' | 'start' | 'end';
}

/** A landmark drawn on the map — decoration only, never a link. */
export type JourneyLandmark =
	| { kind: 'hills'; x: number; y: number; scale?: number }
	| { kind: 'cross'; x: number; y: number }
	| { kind: 'castle'; x: number; y: number }
	| { kind: 'slough'; x: number; y: number }
	| { kind: 'river'; d: string }
	| { kind: 'city'; x: number; y: number };

export interface JourneyMapConfig {
	/** The edition's language: the names are its words. */
	language: string;
	/** The section heading — the book's own register, in its language. */
	title: string;
	/** Which part of the book the road covers (the map's scope line). */
	scope: string;
	stops: JourneyStop[];
	landmarks: JourneyLandmark[];
}

export const MAP_WIDTH = 720;
export const MAP_HEIGHT = 360;

export const JOURNEY_MAPS: Record<string, JourneyMapConfig> = {
	'pilgrims-progress': {
		language: 'en',
		title: "The pilgrim's road",
		scope: "Part One: Christian's journey",
		stops: [
			{ name: 'City of Destruction', chapter: 2, evidence: 'city of Destruction', x: 70, y: 300, label: 'below' },
			{ name: 'Slough of Despond', chapter: 2, evidence: 'Slough of Despond', x: 130, y: 250, label: 'above' },
			{ name: 'Wicket Gate', chapter: 3, evidence: 'Knock, and it shall be opened', x: 190, y: 300, label: 'below' },
			{ name: "Interpreter's House", chapter: 3, evidence: 'Interpreter', x: 250, y: 245, label: 'above' },
			{ name: 'The Cross', chapter: 4, evidence: 'came up with the cross', x: 300, y: 300, label: 'below' },
			{ name: 'Hill Difficulty', chapter: 4, evidence: 'Difficulty', x: 330, y: 215, label: 'start' },
			{ name: 'House Beautiful', chapter: 4, evidence: 'Beautiful', x: 380, y: 150, label: 'above' },
			{ name: 'Valley of Humiliation', chapter: 5, evidence: 'valley of Humiliation', x: 430, y: 215, label: 'end' },
			{ name: 'Valley of the Shadow of Death', chapter: 5, evidence: 'Valley of the Shadow of Death', x: 452, y: 300, label: 'below' },
			{ name: 'Vanity Fair', chapter: 7, evidence: 'Vanity Fair', x: 540, y: 272, label: 'below' },
			{ name: 'Doubting Castle', chapter: 8, evidence: 'Doubting Castle', x: 604, y: 226, label: 'end' },
			{ name: 'Delectable Mountains', chapter: 9, evidence: 'Delectable Mountains', x: 556, y: 160, label: 'start' },
			{ name: 'Enchanted Ground', chapter: 10, evidence: 'Enchanted Ground', x: 600, y: 104, label: 'start' },
			{ name: 'Celestial City', chapter: 11, evidence: 'builded of pearls', x: 672, y: 48, label: 'start' }
		],
		landmarks: [
			{ kind: 'slough', x: 130, y: 262 },
			{ kind: 'cross', x: 324, y: 290 },
			{ kind: 'hills', x: 360, y: 218, scale: 1 },
			{ kind: 'castle', x: 630, y: 254 },
			{ kind: 'hills', x: 590, y: 160, scale: 1.1 },
			{ kind: 'river', d: 'M598,16 C640,50 662,78 650,110 S668,150 714,160' },
			{ kind: 'city', x: 672, y: 48 }
		]
	}
};

/** The map for this edition, if it has one. */
export function journeyMapFor(slug: string, language: string): JourneyMapConfig | null {
	const map = JOURNEY_MAPS[slug];
	return map && map.language === language ? map : null;
}
