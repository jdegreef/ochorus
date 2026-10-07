// hex-ok-file: the browser-chrome colours (<meta name="theme-color">) and the
// picker's swatches must be literal colours — a var() can't be read there, and
// a swatch shows a palette that is not the one applied. Each value equals the
// palette's --bg / --accent in app.css (palettes.test.ts checks it).

import { liturgicalSeason, SEASON_COLOUR, type SeasonColour } from './liturgical';

/**
 * Library palettes — the reader's choice of colours, layered over the theme
 * (light / sepia / dark stays the brightness choice). The CSS is app.css's
 * PALETTES block; the store is palette.svelte.ts; app.html's boot script
 * applies the stored value before first paint. 'parchment' is the house
 * palette and sets no attribute.
 *
 * A CHOICE is not always the palette APPLIED: 'liturgical' ("Church year")
 * follows the season, so on any day it applies one of four seasonal palettes —
 * violet (Advent, Lent), feast (white and gold: Christmas, Epiphany, Easter),
 * flame (red: Holy Week, Pentecost) or olive (green: Ordinary Time, the Olive
 * Grove palette a reader can also pick outright). Only applied palettes have
 * CSS, chrome colours and swatches.
 */
export type Palette =
	| 'parchment'
	| 'cathedral'
	| 'olive'
	| 'hearth'
	| 'dawn'
	| 'monastery'
	| 'illuminated'
	| 'liturgical';
export type AppliedPalette = Exclude<Palette, 'liturgical'> | 'violet' | 'feast' | 'flame';

/** What a reader can choose, in picker order. */
export const PALETTES: readonly Palette[] = [
	'parchment',
	'cathedral',
	'olive',
	'hearth',
	'dawn',
	'monastery',
	'illuminated',
	'liturgical'
];

/** The localStorage key — a bare string, so the boot script can read it. */
export const PALETTE_KEY = 'ochorus:palette';
/** The palette a choice last applied, when that differs from the choice (the
 *  Church year's season), cached so the boot script can paint it before the
 *  app — and its calendar — has loaded. */
export const APPLIED_PALETTE_KEY = 'ochorus:palette-applied';

/** `v` if it is one of `list`, else the house palette. */
const oneOf = <T extends string>(list: readonly T[], v: string | null | undefined): T =>
	(list as readonly string[]).includes(v ?? '') ? (v as T) : ('parchment' as T);

export const normalizePalette = (v: string | null | undefined): Palette => oneOf(PALETTES, v);
export const normalizeApplied = (v: string | null | undefined): AppliedPalette => oneOf(APPLIED_PALETTES, v);

/** The palette each liturgical colour applies. */
const SEASON_PALETTE: Record<SeasonColour, AppliedPalette> = {
	violet: 'violet',
	white: 'feast',
	red: 'flame',
	green: 'olive'
};

/** The palette a choice applies on `date` — itself, except for the Church
 *  year, which applies its season's. */
export function appliedPalette(p: Palette, date: Date = new Date()): AppliedPalette {
	return p === 'liturgical' ? SEASON_PALETTE[SEASON_COLOUR[liturgicalSeason(date)]] : p;
}

/** Per applied palette, the light and dark --bg (browser chrome) and the
 *  swatch the picker draws in each brightness — ground, accent, and a second
 *  colour. */
type Swatch = [ground: string, accent: string, second: string];
/** What a picker draws for a CHOICE: the swatch of the palette it applies
 *  today, and — for a choice that is not one palette — a `mark` of its own. */
type ChoiceSwatch = [ground: string, accent: string, second: string, mark?: string];
export const PALETTE_COLORS: Record<AppliedPalette, { light: string; dark: string; swatch: { light: Swatch; dark: Swatch } }> = {
	parchment: {
		light: '#faf6ef',
		dark: '#16130f',
		swatch: { light: ['#faf6ef', '#3f3d9a', '#b07d22'], dark: ['#16130f', '#9c9af2', '#e0b45c'] }
	},
	cathedral: {
		light: '#f5f6f8',
		dark: '#10141c',
		swatch: { light: ['#f5f6f8', '#1f3a6e', '#b07d22'], dark: ['#10141c', '#93b4ee', '#e0b45c'] }
	},
	olive: {
		light: '#f6f5ee',
		dark: '#121510',
		swatch: { light: ['#f6f5ee', '#2f5a3a', '#9fd0a8'], dark: ['#121510', '#9fd0a8', '#2f5a3a'] }
	},
	hearth: {
		light: '#fbf4ec',
		dark: '#1a120e',
		swatch: { light: ['#fbf4ec', '#8c3b1e', '#eba98a'], dark: ['#1a120e', '#eba98a', '#8c3b1e'] }
	},
	dawn: {
		light: '#fbf6f6',
		dark: '#17121a',
		swatch: { light: ['#fbf6f6', '#6b3a7a', '#d3a8e6'], dark: ['#17121a', '#d3a8e6', '#6b3a7a'] }
	},
	monastery: {
		light: '#f6f6f4',
		dark: '#141414',
		swatch: { light: ['#f6f6f4', '#3b4a5c', '#a9bdd4'], dark: ['#141414', '#a9bdd4', '#3b4a5c'] }
	},
	illuminated: {
		light: '#f7f1e3',
		dark: '#13141f',
		swatch: { light: ['#f7f1e3', '#1f3f8f', '#b3341f'], dark: ['#13141f', '#9fb4f5', '#f08a6e'] }
	},
	violet: {
		light: '#f7f5fa',
		dark: '#15121c',
		swatch: { light: ['#f7f5fa', '#4f2d7f', '#c3a8f0'], dark: ['#15121c', '#c3a8f0', '#4f2d7f'] }
	},
	feast: {
		light: '#fcfaf4',
		dark: '#17150f',
		swatch: { light: ['#fcfaf4', '#7a5a10', '#e6c66e'], dark: ['#17150f', '#e6c66e', '#7a5a10'] }
	},
	flame: {
		light: '#fbf6f5',
		dark: '#1a1112',
		swatch: { light: ['#fbf6f5', '#962a26', '#f09a8f'], dark: ['#1a1112', '#f09a8f', '#962a26'] }
	}
};

/** Every palette app.css styles — the choosable ones bar 'liturgical', and
 *  the seasonal ones it resolves to. PALETTE_COLORS' keys, so the two can't
 *  drift. */
export const APPLIED_PALETTES = Object.keys(PALETTE_COLORS) as AppliedPalette[];

/** The Church year's own mark: its seasons' accents as quarters of a disc —
 *  what tells it apart from the one palette it wears today (in Ordinary Time,
 *  Olive Grove's swatch exactly). */
const wheel = (mode: 'light' | 'dark') => {
	const [a, b, c, d] = Object.values(SEASON_PALETTE).map((p) => PALETTE_COLORS[p].swatch[mode][1]);
	return `conic-gradient(${a} 0 25%, ${b} 0 50%, ${c} 0 75%, ${d} 0)`;
};
export const SEASON_WHEEL = { light: wheel('light'), dark: wheel('dark') };

/** The swatch a picker draws for a choice: the palette it applies today (so
 *  the Church year shows its season), plus the Church year's wheel as its
 *  mark. Pickers draw what they get and never name a palette. */
export function swatchOf(p: Palette, mode: 'light' | 'dark', date: Date = new Date()): ChoiceSwatch {
	const swatch = PALETTE_COLORS[appliedPalette(p, date)].swatch[mode];
	return p === 'liturgical' ? [...swatch, SEASON_WHEEL[mode]] : swatch;
}
