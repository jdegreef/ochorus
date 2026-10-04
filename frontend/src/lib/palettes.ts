// hex-ok-file: the browser-chrome colours (<meta name="theme-color">) and the
// picker's swatches must be literal colours — a var() can't be read there, and
// a swatch shows a palette that is not the one applied. Each value equals the
// palette's --bg / --accent in app.css (palettes.test.ts checks it).

/**
 * Library palettes — the reader's choice of colours, layered over the theme
 * (light / sepia / dark stays the brightness choice). The CSS is app.css's
 * PALETTES block; the store is palette.svelte.ts; app.html's boot script
 * applies the stored value before first paint. 'parchment' is the house
 * palette and sets no attribute.
 */
export type Palette = 'parchment' | 'cathedral' | 'olive' | 'hearth' | 'dawn' | 'monastery';

export const PALETTES: readonly Palette[] = ['parchment', 'cathedral', 'olive', 'hearth', 'dawn', 'monastery'];

/** The localStorage key — a bare string, so the boot script can read it. */
export const PALETTE_KEY = 'ochorus:palette';

export function normalizePalette(v: string | null | undefined): Palette {
	return (PALETTES as readonly string[]).includes(v ?? '') ? (v as Palette) : 'parchment';
}

/** Per palette, the light and dark --bg (browser chrome) and the swatch the
 *  picker draws in each brightness — ground, accent, and a second colour. */
type Swatch = [ground: string, accent: string, second: string];
export const PALETTE_COLORS: Record<Palette, { light: string; dark: string; swatch: { light: Swatch; dark: Swatch } }> = {
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
	}
};
