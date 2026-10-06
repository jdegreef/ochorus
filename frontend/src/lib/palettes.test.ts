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
import { normalizePalette, PALETTE_COLORS, PALETTE_KEY, PALETTES } from './palettes';
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

const CUSTOM = PALETTES.filter((p) => p !== 'parchment');

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
	// line sits where the scrim is 75% tint over a painting that may be white,
	// so every tint is composited at 75% over white and must still carry the
	// hero's ink at 4.5:1.
	const heroRoot = (() => {
		const start = CSS.search(/:root \{\s*--hero-ink:/);
		const body = CSS.slice(start, CSS.indexOf('}', start));
		return Object.fromEntries([...body.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
	})();
	for (const p of PALETTES) {
		it(`${p}: the home hero's date line clears 4.5:1 over a white painting`, () => {
			const tint = p === 'parchment' ? heroRoot['--hero-tint'] : block(`:root[data-palette='${p}']`)['--hero-tint'];
			expect(tint, `${p} has no --hero-tint`).toMatch(/^#[0-9a-f]{6}$/i);
			const ground = rgb(tint).map((c) => c * 0.75 + 255 * 0.25);
			expect(contrastRatio(rgb(heroRoot['--hero-ink']), ground)).toBeGreaterThanOrEqual(4.5);
		});
	}

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

	it('hydrates from storage', () => {
		localStorage.setItem(PALETTE_KEY, 'dawn');
		palette.init();
		expect(palette.current).toBe('dawn');
		expect(document.documentElement.dataset.palette).toBe('dawn');
	});
});
