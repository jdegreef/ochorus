import type { IconName } from '$lib/components/Icon.svelte';

/**
 * Per-topic visual identity — a curated accent hue + a themed line-icon so each
 * shelf reads as its own thing rather than one more identical card. Kept on the
 * client (not the API) because it's presentation, not content, and the topic set
 * is small and stable; an unmapped slug falls back to a neutral accent + tag.
 *
 * The accent is used for tints (via color-mix) and the icon colour, never as
 * body text, so it stays legible in both themes.
 */
export interface TopicMeta {
	accent: string;
	icon: IconName;
}

const META: Record<string, TopicMeta> = {
	prayer: { accent: '#5257c9', icon: 'sparkle' }, // the secret place / devotion
	'holy-spirit': { accent: '#d98324', icon: 'wind' }, // the rushing wind (Acts 2)
	'deeper-life': { accent: '#149e93', icon: 'mountain' }, // going further in
	'grace-and-comfort': { accent: '#d1567b', icon: 'heart' }, // comfort for the weary
	'revival-and-missions': { accent: '#df552f', icon: 'flame' }, // a burning heart
	'faith-and-guidance': { accent: '#4f9a3e', icon: 'compass' } // walking by faith
};

const FALLBACK: TopicMeta = { accent: '#3b5bdb', icon: 'tag' };

export const topicMeta = (slug: string): TopicMeta => META[slug] ?? FALLBACK;

/**
 * The curated accents, as a list — for surfaces that need a distinct colour per
 * item but have no topic to look up (reading plans).
 *
 * Deriving a plan's hue from its first cover was the obvious move and looked
 * wrong: most covers are dark navy or black, so every plan card came out the
 * same muted blue and the shelf lost exactly the colour that makes the Topics
 * page work. Cycling the curated palette by a stable hash of the slug keeps the
 * cards vivid and distinct, and a given plan always gets the same colour.
 */
export const ACCENTS: string[] = Object.values(META).map((m) => m.accent);

/** Stable per-slug pick from ACCENTS (FNV-1a, so it doesn't shift as slugs are added). */
export function accentForSlug(slug: string): string {
	let h = 0x811c9dc5;
	for (let i = 0; i < slug.length; i++) {
		h ^= slug.charCodeAt(i);
		h = Math.imul(h, 0x01000193) >>> 0;
	}
	return ACCENTS[h % ACCENTS.length];
}
