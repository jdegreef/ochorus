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
export type Palette = 'parchment' | 'cathedral' | 'olive' | 'hearth' | 'dawn' | 'monastery' | 'liturgical';
export type AppliedPalette = Exclude<Palette, 'liturgical'> | 'violet' | 'feast' | 'flame';

/** What a reader can choose, in picker order. */
export const PALETTES: readonly Palette[] = ['parchment', 'cathedral', 'olive', 'hearth', 'dawn', 'monastery', 'liturgical'];

/** Every palette app.css styles — the choosable ones bar 'liturgical', and
 *  the seasonal ones it resolves to. */
export const APPLIED_PALETTES: readonly AppliedPalette[] = [
	'parchment',
	'cathedral',
	'olive',
	'hearth',
	'dawn',
	'monastery',
	'violet',
	'feast',
	'flame'
];

/** The localStorage key — a bare string, so the boot script can read it. */
export const PALETTE_KEY = 'ochorus:palette';
/** The palette last applied for the Church year, cached so the boot script
 *  can paint the season before the app (and its calendar) has loaded. */
export const APPLIED_PALETTE_KEY = 'ochorus:palette-applied';

export function normalizePalette(v: string | null | undefined): Palette {
	return (PALETTES as readonly string[]).includes(v ?? '') ? (v as Palette) : 'parchment';
}

export function normalizeApplied(v: string | null | undefined): AppliedPalette {
	return (APPLIED_PALETTES as readonly string[]).includes(v ?? '') ? (v as AppliedPalette) : 'parchment';
}

/** The palette each liturgical colour applies. */
export const SEASON_PALETTE: Record<SeasonColour, AppliedPalette> = {
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

/** The swatch a picker draws for a choice: the Church year shows today's
 *  season, so the reader sees what they are about to get. */
export function swatchOf(p: Palette, mode: 'light' | 'dark', date: Date = new Date()): Swatch {
	return PALETTE_COLORS[appliedPalette(p, date)].swatch[mode];
}
