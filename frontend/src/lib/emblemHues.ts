/**
 * The dominant ink of every emblem, precomputed.
 *
 * GENERATED — do not edit by hand. Run `npm run emblem:hues` after changing
 * emblem art; `emblemHues.test.ts` fails if this file and `emblemHue()`
 * disagree.
 *
 * This exists so a surface can wear an emblem's colour without importing the
 * emblem's DRAWING. `emblemHue()` reads the art to derive the hue, and the art
 * is 51 SVG strings that Rollup cannot tree-shake apart — the sermon plate
 * importing it cost the home page and every sermon page 10.6 KB gzip on the
 * critical path, for one colour.
 *
 * hex-ok-file: these are the colours OF the drawings, the way a book cover has
 * colours — data, not chrome that should restyle with the theme.
 */
import type { EmblemName } from './emblems';

export const EMBLEM_HUES: Record<EmblemName, string> = {
	'alabaster-jar': '#cf5c85',
	'alpha-omega': '#d9a441',
	'ark-rainbow': '#d9a441',
	'basin-towel': '#1e6b63',
	'broken-chain': '#3c5970',
	'bruised-reed': '#3d7434',
	'candle-and-book': '#5f4227',
	'chi-rho': '#d9a441',
	'compass-rose': '#d9a441',
	'cornerstone': '#a97a24',
	'cross-sunrise': '#d9a441',
	'dawn-over-hills': '#d9a441',
	'desert-spring': '#a7c9e8',
	'door-ajar': '#d9a441',
	'dove-descending': '#d9a441',
	'eagles-wings': '#a97a24',
	'easy-yoke': '#d9a441',
	'feast-table': '#d9a441',
	'field-sunrise': '#d9a441',
	'fourth-in-fire': '#d9a441',
	'golden-key': '#d9a441',
	'gospel-banner': '#a97a24',
	'grace-fountain': '#4a6fb5',
	'grafted-branch': '#8a5fbf',
	'heavens-ladder': '#d9a441',
	'herald-trumpet': '#a97a24',
	'ichthys-fish': '#1e6b63',
	'jar-of-balm': '#cf5c85',
	'joyful-harp': '#d9a441',
	'kneeling-light': '#2d4a80',
	'laurel-tome': '#5a9e4d',
	'loaf-and-cup': '#a97a24',
	'mission-ship': '#5f4227',
	'morning-star': '#4a6fb5',
	'mountain-dawn': '#d9a441',
	'mountain-into-sea': '#4a6fb5',
	'mustard-tree': '#5a9e4d',
	'narrow-gate': '#d9a441',
	'new-sprout': '#d9a441',
	'oil-lamp': '#d9a441',
	'olive-press': '#5a9e4d',
	'open-hands': '#d9a441',
	'open-word': '#5f4227',
	'overflowing-cup': '#a97a24',
	'paradise-palms': '#d9a441',
	'paschal-lamb': '#5f4227',
	'pearl-of-price': '#1e6b63',
	'pentecost-fire': '#d9a441',
	'pilgrim-road': '#a97a24',
	'poured-out': '#d9a441',
	'praying-hands': '#d9a441',
	'raised-lantern': '#a97a24',
	'ravens-bread': '#273748',
	'refiners-crucible': '#d9a441',
	'rising-incense': '#a97a24',
	'river-sunrise': '#d9a441',
	'rock-unmoved': '#3c5970',
	'rooted-sapling': '#5a9e4d',
	'rose-among-thorns': '#3d7434',
	'sealed-scroll': '#d95f43',
	'sheltered-lamp': '#d9a441',
	'sheltering-wings': '#a97a24',
	'shepherd-crook': '#3c5970',
	'shield-of-faith': '#d9a441',
	'still-waters': '#2f8f85',
	'sun-and-moon': '#d9a441',
	'sword-and-shield': '#a97a24',
	'torch-globe': '#5a9e4d',
	'true-vine': '#8a5fbf',
	'warmed-heart': '#d9a441',
	'watchmans-bell': '#a97a24',
	'waymark': '#4a6fb5',
	'wheat-sheaf': '#d9a441'
};
