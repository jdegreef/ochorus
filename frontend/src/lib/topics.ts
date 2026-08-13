import { fallbackEmblem, type EmblemName } from '$lib/emblems';

/**
 * Per-topic visual identity — a curated accent hue + a themed multicolour
 * emblem (see $lib/emblems.ts) so each shelf reads as its own thing rather
 * than one more identical card. Kept on the client (not the API) because it's
 * presentation, not content, and the topic set is small and stable; an
 * unmapped slug falls back to a neutral accent + a stable generic emblem.
 *
 * The accent is used for tints (via color-mix), never as body text, so it
 * stays legible in both themes.
 */
export interface TopicMeta {
	accent: string;
	emblem: EmblemName;
}

const META: Record<string, TopicMeta> = {
	prayer: { accent: '#5257c9', emblem: 'praying-hands' }, // the secret place / devotion
	'holy-spirit': { accent: '#d98324', emblem: 'dove-descending' }, // the dove, the rushing wind (Acts 2)
	'deeper-life': { accent: '#149e93', emblem: 'mountain-dawn' }, // going further in
	'grace-and-comfort': { accent: '#d1567b', emblem: 'overflowing-cup' }, // comfort for the weary
	'revival-and-missions': { accent: '#df552f', emblem: 'torch-globe' }, // a burning heart
	'faith-and-guidance': { accent: '#4f9a3e', emblem: 'compass-rose' }, // walking by faith
	'the-gospel-call': { accent: '#b8912f', emblem: 'herald-trumpet' }, // the herald's invitation
	'enduring-classics': { accent: '#8a5bbf', emblem: 'laurel-tome' }, // the old paths, still good
	'the-way-of-holiness': { accent: '#3e7cb8', emblem: 'narrow-gate' }, // strait is the gate
	'the-preached-word': { accent: '#946b4a', emblem: 'open-word' } // the wooden pulpit
};

export const topicMeta = (slug: string): TopicMeta =>
	META[slug] ?? { accent: '#3b5bdb', emblem: fallbackEmblem(slug) };
