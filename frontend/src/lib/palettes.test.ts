/**
 * Library palettes (app.css "PALETTES") — measured, not trusted.
 *
 * A palette re-tints the grounds and the accent over a theme, so every ink the
 * theme already promised at 4.5:1 has to be re-measured on the new grounds:
 * text, muted, the accent and all six section hues on --bg, --surface,
 * --surface-2 and --band; the accent on its own soft tint; the accent's
 * contrast ink on the accent (a primary button). Then the three places that
 * restate a palette — palettes.ts, the app.html boot script and the store —
 * are held to the CSS.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { beforeEach, describe, expect, it } from 'vitest';
import { contrastRatio } from './coverArt';
import {
	APPLIED_PALETTE_KEY,
	APPLIED_PALETTES,
	appliedPalette,
	normalizePalette,
	PALETTE_COLORS,
	PALETTE_KEY,
	PALETTES,
	SEASON_WHEEL,
	swatchOf
} from './palettes';
import { palette } from './palette.svelte';

const CSS = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8').replace(/\/\*[\s\S]*?\*\//g, '');
const HTML = readFileSync(join(process.cwd(), 'src/app.html'), 'utf-8');
const HUES = ['indigo', 'oxblood', 'cypress', 'ochre', 'slate', 'plum'];
const GROUNDS = ['--bg', '--surface', '--surface-2', '--band'];

function block(selector: string): Record<string, string> {
	const start = CSS.indexOf(`${selector} {`);
	if (start === -1) return {};
	const body = CSS.slice(start, CSS.indexOf('}', start));
	const vars: Record<string, string> = {};
	for (const m of body.matchAll(/(--[\w-]+):\s*([^;]+);/g)) vars[m[1]] = m[2].trim();
	return vars;
}
/** The bare-:root theme block (lamplight) — the one that opens with --bg. */
const lamplight = (() => {
	const start = CSS.search(/:root \{\s*--bg:/);
	const body = CSS.slice(start, CSS.indexOf('}', start));
	const vars: Record<string, string> = {};
	for (const m of body.matchAll(/(--[\w-]+):\s*([^;]+);/g)) vars[m[1]] = m[2].trim();
	return vars;
})();
const theme = (mode: 'light' | 'dark' | 'sepia') =>
	mode === 'dark' ? lamplight : { ...lamplight, ...block(`:root[data-theme='${mode}']`) };
const paletteBlock = (mode: string, p: string) => block(`:root[data-theme='${mode}'][data-palette='${p}']`);

const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const ratio = (a: string, b: string) => contrastRatio(rgb(a), rgb(b));

// Every palette app.css styles: the choosable ones and the Church year's
// seasonal ones ('liturgical' itself is a choice with no CSS of its own).
const CUSTOM = APPLIED_PALETTES.filter((p) => p !== 'parchment');

describe('library palettes', () => {
	for (const p of CUSTOM) {
		for (const mode of ['light', 'dark', 'sepia'] as const) {
			it(`${p} in ${mode}: every ink clears 4.5:1 on every ground`, () => {
				const own = paletteBlock(mode, p);
				expect(own['--accent'], `${p} has no ${mode} block`).toMatch(/^#[0-9a-f]{6}$/i);
				const vars = { ...theme(mode), ...own };
				const failures: string[] = [];
				const inks = ['--text', '--muted', '--accent', ...HUES.map((h) => `--hue-${h}`)];
				for (const ink of inks)
					for (const ground of GROUNDS) {
						const r = ratio(vars[ink], vars[ground]);
						if (r < 4.5) failures.push(`${ink} on ${ground}: ${r.toFixed(2)}`);
					}
				// A section hue is also text on its own soft tint (a chip, a tile).
				for (const h of HUES) {
					const r = ratio(vars[`--hue-${h}`], vars[`--hue-${h}-soft`]);
					if (r < 4.5) failures.push(`--hue-${h} on its soft: ${r.toFixed(2)}`);
				}
				// A section band (app.css .section-band): each hue's soft wash
				// half-mixed into the palette's page, under body text, muted, the
				// accent and the hue itself.
				for (const h of HUES) {
					const soft = rgb(vars[`--hue-${h}-soft`]);
					const bg = rgb(vars['--bg']);
					const ground = soft.map((c, i) => Math.round((c + bg[i]) / 2));
					for (const ink of ['--text', '--muted', '--accent', `--hue-${h}`]) {
						const r = contrastRatio(rgb(vars[ink]), ground);
						if (r < 4.5) failures.push(`${ink} on the ${h} band: ${r.toFixed(2)}`);
					}
				}
				// A palette's own initial ink (Illuminated's vermilion) is display
				// type at 3em: large text, so 3:1 on the reading grounds.
				if (own['--initial'])
					for (const ground of ['--bg', '--surface']) {
						const r = ratio(own['--initial'], vars[ground]);
						if (r < 3) failures.push(`--initial on ${ground}: ${r.toFixed(2)}`);
					}
				// The ornament metal paints the settings gear: a control, so 3:1.
				const metal = vars['--ornament'] === 'var(--gold)' ? vars['--gold'] : vars['--ornament'];
				for (const ground of ['--bg', '--surface']) {
					const r = ratio(metal, vars[ground]);
					if (r < 3) failures.push(`--ornament on ${ground}: ${r.toFixed(2)}`);
				}
				for (const [ink, ground] of [
					['--accent', '--accent-soft'],
					['--accent-contrast', '--accent']
				]) {
					const r = ratio(vars[ink], vars[ground]);
					if (r < 4.5) failures.push(`${ink} on ${ground}: ${r.toFixed(2)}`);
				}
				expect(failures, failures.join('\n')).toEqual([]);
			});
		}

		it(`${p}: palettes.ts and the boot script restate its CSS`, () => {
			expect(PALETTE_COLORS[p].light).toBe(paletteBlock('light', p)['--bg']);
			expect(PALETTE_COLORS[p].dark).toBe(paletteBlock('dark', p)['--bg']);
			expect(PALETTE_COLORS[p].swatch.light.slice(0, 2)).toEqual([
				paletteBlock('light', p)['--bg'],
				paletteBlock('light', p)['--accent']
			]);
			expect(PALETTE_COLORS[p].swatch.dark.slice(0, 2)).toEqual([
				paletteBlock('dark', p)['--bg'],
				paletteBlock('dark', p)['--accent']
			]);
			expect(HTML).toContain(`${p}: { light: '${PALETTE_COLORS[p].light}', dark: '${PALETTE_COLORS[p].dark}' }`);
		});
	}

	// The home hero's scrim is the palette's --hero-tint, not black. The date
	// line sits where the scrim is at least 75% tint (it holds 75% up to 85% of
	// the hero's height) over a painting that may be white,
	// so every tint is composited at 75% over white and must still carry the
	// hero's ink at 4.5:1.
	const heroRoot = (() => {
		const start = CSS.search(/:root \{\s*--hero-ink:/);
		const body = CSS.slice(start, CSS.indexOf('}', start));
		return Object.fromEntries([...body.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
	})();
	it("the hero scrim holds 75% tint up to 85% of the hero's height", () => {
		// What the composite below assumes; lower the stop and a wrapped
		// greeting lifts the date line into a thinner scrim.
		expect(heroRoot['--hero-scrim']).toMatch(/var\(--hero-tint\) 75%, transparent\) 85%/);
	});
	for (const p of APPLIED_PALETTES) {
		it(`${p}: the home hero's date line clears 4.5:1 over a white painting`, () => {
			const tint = p === 'parchment' ? heroRoot['--hero-tint'] : block(`:root[data-palette='${p}']`)['--hero-tint'];
			expect(tint, `${p} has no --hero-tint`).toMatch(/^#[0-9a-f]{6}$/i);
			const ground = rgb(tint).map((c) => c * 0.75 + 255 * 0.25);
			expect(contrastRatio(rgb(heroRoot['--hero-ink']), ground)).toBeGreaterThanOrEqual(4.5);
		});
	}

	// The book page's band: the cover's painting under --wash-veil of the
	// page's ground. Composited over a black and a white painting, its inks —
	// text, the accent, and muted half-way to the text, as the band sets it —
	// must still clear 4.5:1 in every theme and palette.
	it("the book band's veil holds the hero's inks over any painting", () => {
		const veil = parseFloat(heroRoot['--wash-veil']) / 100;
		expect(veil).toBeGreaterThan(0.5);
		const failures: string[] = [];
		for (const mode of ['light', 'dark', 'sepia'] as const)
			for (const p of APPLIED_PALETTES) {
				const vars = p === 'parchment' ? theme(mode) : { ...theme(mode), ...paletteBlock(mode, p) };
				const text = rgb(vars['--text']);
				const inks = {
					'--text': text,
					'--accent': rgb(vars['--accent']),
					'--muted (band)': rgb(vars['--muted']).map((c, i) => (c + text[i]) / 2)
				};
				for (const paint of [0, 255]) {
					const ground = rgb(vars['--bg']).map((c) => c * veil + paint * (1 - veil));
					for (const [ink, c] of Object.entries(inks)) {
						const r = contrastRatio(c, ground);
						if (r < 4.5) failures.push(`${mode}/${p}: ${ink} over ${paint ? 'white' : 'black'}: ${r.toFixed(2)}`);
					}
				}
			}
		expect(failures, failures.join('\n')).toEqual([]);
	});

	it("the painting's label holds on the hero's mat", () => {
		expect(ratio(heroRoot['--hero-mat-ink'], heroRoot['--hero-mat'])).toBeGreaterThanOrEqual(4.5);
	});

	it("the house palette's chrome colours are the themes' own", () => {
		expect(PALETTE_COLORS.parchment.light).toBe(theme('light')['--bg']);
		expect(PALETTE_COLORS.parchment.dark).toBe(lamplight['--bg']);
		expect(PALETTE_COLORS.parchment.swatch.light[1]).toBe(theme('light')['--accent']);
		expect(PALETTE_COLORS.parchment.swatch.dark[1]).toBe(lamplight['--accent']);
	});

	it("the API accepts exactly these palettes (backend accounts/models.py PALETTES)", () => {
		const models = readFileSync(join(process.cwd(), '../backend/accounts/models.py'), 'utf-8');
		const tuple = models.match(/^PALETTES = \(([^)]*)\)/m);
		expect(tuple, 'PALETTES tuple not found in accounts/models.py').toBeTruthy();
		const backend = [...tuple![1].matchAll(/"([a-z]+)"/g)].map((m) => m[1]);
		expect(backend).toEqual([...PALETTES]);
	});

	it('the boot script reads the store key', () => {
		expect(HTML).toContain(`getItem('${PALETTE_KEY}')`);
	});

	it("the boot script paints the Church year's cached season", () => {
		expect(HTML).toContain(`localStorage.getItem('${APPLIED_PALETTE_KEY}') || localStorage.getItem('${PALETTE_KEY}')`);
	});
});

describe('the Church year', () => {
	const on = (y: number, m: number, d: number) => appliedPalette('liturgical', new Date(y, m - 1, d));

	it('applies the season\'s colour', () => {
		expect(on(2026, 12, 6)).toBe('violet'); // Advent
		expect(on(2026, 12, 25)).toBe('feast'); // Christmas
		expect(on(2026, 1, 6)).toBe('feast'); // Epiphany
		expect(on(2026, 3, 4)).toBe('violet'); // Lent
		expect(on(2026, 3, 30)).toBe('flame'); // Holy Week
		expect(on(2026, 4, 12)).toBe('feast'); // Easter
		expect(on(2026, 5, 24)).toBe('flame'); // Pentecost
		expect(on(2026, 10, 6)).toBe('olive'); // Ordinary Time
	});

	it('leaves every other choice as it is', () => {
		for (const p of PALETTES.filter((p) => p !== 'liturgical')) expect(appliedPalette(p)).toBe(p);
	});

	it("draws today's season as its swatch", () => {
		const advent = new Date(2026, 11, 6);
		expect(swatchOf('liturgical', 'light', advent)).toEqual([...PALETTE_COLORS.violet.swatch.light, SEASON_WHEEL.light]);
		expect(swatchOf('liturgical', 'dark', advent)).toEqual([...PALETTE_COLORS.violet.swatch.dark, SEASON_WHEEL.dark]);
		expect(swatchOf('olive', 'light')).toHaveLength(3);
	});

	it('has a mark of its own: all four seasons, never one palette', () => {
		// In Ordinary Time it wears Olive Grove exactly; the wheel is what tells
		// the two apart in a picker.
		for (const mode of ['light', 'dark'] as const) {
			const wheel = SEASON_WHEEL[mode];
			for (const p of ['violet', 'feast', 'flame', 'olive'] as const)
				expect(wheel).toContain(PALETTE_COLORS[p].swatch[mode][1]);
		}
	});
});

describe('palette store', () => {
	beforeEach(() => {
		localStorage.clear();
		delete document.documentElement.dataset.palette;
	});

	it('normalises unknown values to the house palette', () => {
		expect(normalizePalette(null)).toBe('parchment');
		expect(normalizePalette('neon')).toBe('parchment');
		expect(normalizePalette('hearth')).toBe('hearth');
	});

	it('applies and persists a palette, and clears both for the house one', () => {
		palette.set('cathedral');
		expect(document.documentElement.dataset.palette).toBe('cathedral');
		expect(localStorage.getItem(PALETTE_KEY)).toBe('cathedral');
		palette.set('parchment');
		expect(document.documentElement.dataset.palette).toBeUndefined();
		expect(localStorage.getItem(PALETTE_KEY)).toBeNull();
	});

	it('re-colours the browser chrome to the palette', () => {
		const meta = document.head.appendChild(document.createElement('meta'));
		meta.name = 'theme-color';
		document.documentElement.setAttribute('data-theme', 'light');
		palette.set('olive');
		expect(meta.getAttribute('content')).toBe(PALETTE_COLORS.olive.light);
		meta.remove();
	});

	it('stores the Church year as the choice, paints the season, and caches it for boot', () => {
		palette.set('liturgical');
		const season = appliedPalette('liturgical');
		expect(localStorage.getItem(PALETTE_KEY)).toBe('liturgical');
		expect(palette.applied).toBe(season);
		expect(document.documentElement.dataset.palette).toBe(season);
		expect(localStorage.getItem(APPLIED_PALETTE_KEY)).toBe(season);
		palette.set('hearth');
		expect(localStorage.getItem(APPLIED_PALETTE_KEY)).toBeNull();
	});

	it('hydrates from storage', () => {
		localStorage.setItem(PALETTE_KEY, 'dawn');
		palette.init();
		expect(palette.current).toBe('dawn');
		expect(document.documentElement.dataset.palette).toBe('dawn');
	});
});
