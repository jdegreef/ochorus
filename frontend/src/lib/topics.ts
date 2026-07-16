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
