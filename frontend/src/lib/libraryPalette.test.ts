/**
 * The library palette (app.css, "THE LIBRARY PALETTE") — measured, not trusted.
 *
 * Six hues, three themes, and each hue is used as TEXT (a stat tile's number,
 * an active nav label) on five grounds: --bg, --surface, --surface-2, --band
 * (the deeper ground of a `.band` section) and its own -soft tint. That is 90
 * pairs, and STYLE_GUIDE §1 notes sepia is the theme that has actually failed
 * before — so every pair is computed here against WCAG AA (4.5:1) rather than
 * eyeballed in one theme.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { contrastRatio } from './coverArt';

// Comments stripped, so a declaration quoted in prose (`was --hue-ochre: …`)
// can never stand in for the real one.
const CSS = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8').replace(/\/\*[\s\S]*?\*\//g, '');
const HUES = ['indigo', 'oxblood', 'cypress', 'ochre', 'slate', 'plum'];
const SECTIONS = ['books', 'sermons', 'plans', 'topics', 'biographies', 'originals'];

const PAPER = ":root[data-theme='light']";
const SEPIA = ":root[data-theme='sepia']";

/** The custom properties declared in the first block `opener` matches, up to
 *  the first closing brace (comments are stripped, and no value holds one). */
function rules(opener: RegExp): Record<string, string> {
	const start = CSS.search(opener);
	if (start === -1) throw new Error(`${opener} not found in app.css`);
	const body = CSS.slice(start, CSS.indexOf('}', start));
	const vars: Record<string, string> = {};
	for (const m of body.matchAll(/(--[\w-]+):\s*([^;]+);/g)) vars[m[1]] = m[2].trim();
	return vars;
}

/** The theme block opened by `selector {` — the one that sets --bg, since
 *  app.css has other bare `:root` blocks (fonts, sections). */
function block(selector: string): Record<string, string> {
	const escaped = selector.replace(/[[\]()]/g, '\\$&');
	return rules(new RegExp(`${escaped} \\{\\s*--bg:`));
}

const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

const lamplight = block(':root');
const THEMES: Record<string, Record<string, string>> = {
	lamplight,
	paper: { ...lamplight, ...block(PAPER) },
	sepia: { ...lamplight, ...block(SEPIA) }
};

describe('library palette', () => {
	for (const [theme, vars] of Object.entries(THEMES)) {
		it(`every hue clears 4.5:1 on every ground in ${theme}`, () => {
			const failures: string[] = [];
			for (const hue of HUES) {
				const ink = vars[`--hue-${hue}`];
				expect(ink, `--hue-${hue} missing in ${theme}`).toMatch(/^#[0-9a-f]{6}$/i);
				for (const ground of ['--bg', '--surface', '--surface-2', '--band', `--hue-${hue}-soft`]) {
					const ratio = contrastRatio(rgb(ink), rgb(vars[ground]));
					if (ratio < 4.5) failures.push(`${hue} on ${ground}: ${ratio.toFixed(2)}`);
				}
			}
			expect(failures, failures.join('\n')).toEqual([]);
		});

		it(`text, muted and accent clear 4.5:1 on a .band in ${theme}`, () => {
			for (const ink of ['--text', '--muted', '--accent']) {
				const ratio = contrastRatio(rgb(vars[ink]), rgb(vars['--band']));
				expect(ratio, `${ink} on --band`).toBeGreaterThanOrEqual(4.5);
			}
		});
	}

	for (const [theme, selector] of [
		['paper', PAPER],
		['sepia', SEPIA]
	]) {
		it(`${theme} defines every hue and its band itself rather than inheriting lamplight's`, () => {
			const own = block(selector);
			expect(own['--band'], '--band').toBeDefined();
			expect(own['--grain'], '--grain').toBeDefined();
			for (const hue of HUES) {
				expect(own[`--hue-${hue}`], `--hue-${hue}`).toBeDefined();
				expect(own[`--hue-${hue}-soft`], `--hue-${hue}-soft`).toBeDefined();
			}
		});
	}

	describe('the night band', () => {
		// It re-declares its tokens on itself, so the page theme never reaches
		// inside: one measurement covers lamplight, paper and sepia.
		const night = rules(/@media screen \{\s*\.night-band \{/);
		const ratio = (a: string, b: string) => contrastRatio(rgb(night[a]), rgb(night[b]));

		it('every ink clears 4.5:1 on its grounds and every hue on its soft', () => {
			const failures: string[] = [];
			const inks = ['--text', '--muted', '--accent', '--gold', '--danger', '--warning', ...HUES.map((h) => `--hue-${h}`)];
			for (const ink of inks) {
				expect(night[ink], `${ink} missing on .night-band`).toMatch(/^#[0-9a-f]{6}$/i);
				for (const ground of ['--bg', '--surface', '--surface-2']) {
					if (ratio(ink, ground) < 4.5) failures.push(`${ink} on ${ground}: ${ratio(ink, ground).toFixed(2)}`);
				}
			}
			for (const hue of HUES) {
				const r = ratio(`--hue-${hue}`, `--hue-${hue}-soft`);
				if (r < 4.5) failures.push(`${hue} on its soft: ${r.toFixed(2)}`);
			}
			if (ratio('--accent', '--accent-soft') < 4.5) failures.push('accent on accent-soft');
			if (ratio('--accent-contrast', '--accent') < 4.5) failures.push('accent-contrast on accent');
			expect(failures, failures.join('\n')).toEqual([]);
		});

		it('control edges clear 3:1 (WCAG 1.4.11)', () => {
			for (const ground of ['--bg', '--surface', '--surface-2']) {
				expect(ratio('--border-strong', ground), `--border-strong on ${ground}`).toBeGreaterThanOrEqual(3);
			}
		});

		it('is screen-only, and the print reset reaches it', () => {
			// Same specificity as the print reset and later in the file, so an
			// unscoped band rule would win on paper: near-white ink on white.
			expect(CSS).not.toMatch(/\n\.night-band \{\s*--bg:/);
			expect(CSS).toMatch(/@media print \{[\s\S]*?:root\[data-theme\],\s*\.night-band \{\s*--bg: #ffffff;/);
		});
	});

	describe('cover-tinted book cards', () => {
		// A card's ground is its book's cover_color mixed into --surface at
		// --cover-tint-amount (app.css .book-card). Cover colours are floored at
		// mint to carry white type at 4.5:1 (covers.ink_safe), so the lightest a
		// cover can be is a grey of luminance ~0.183 (#767676); the darkest is
		// black. Every ink must hold 4.5:1 across that whole range.
		const mix = (c: number[], g: number[], p: number) => c.map((v, i) => v * p + g[i] * (1 - p));
		const extremes = ['#000000', '#3a3a3a', '#767676', '#0a0a2a', '#856e48', '#7a1f1a'];
		const amount = (vars: Record<string, string>) => parseFloat(vars['--cover-tint-amount']) / 100;

		for (const [theme, vars] of Object.entries(THEMES)) {
			it(`text, muted, accent and every hue clear 4.5:1 on a tinted card in ${theme}`, () => {
				expect(vars['--cover-tint-amount'], '--cover-tint-amount').toMatch(/^\d+(\.\d+)?%$/);
				const failures: string[] = [];
				for (const cover of extremes) {
					const ground = mix(rgb(cover), rgb(vars['--surface']), amount(vars));
					for (const ink of ['--text', '--muted', '--accent', ...HUES.map((h) => `--hue-${h}`)]) {
						const r = contrastRatio(rgb(vars[ink]), ground);
						if (r < 4.5) failures.push(`${ink} over ${cover}: ${r.toFixed(2)}`);
					}
				}
				expect(failures, failures.join('\n')).toEqual([]);
			});
		}

		it('holds on the night band too, whichever theme sets the amount', () => {
			const night = rules(/@media screen \{\s*\.night-band \{/);
			const failures: string[] = [];
			for (const vars of Object.values(THEMES)) {
				for (const cover of extremes) {
					const ground = mix(rgb(cover), rgb(night['--surface']), amount(vars));
					for (const ink of ['--text', '--muted', '--accent']) {
						const r = contrastRatio(rgb(night[ink]), ground);
						if (r < 4.5) failures.push(`${ink} over ${cover} at ${vars['--cover-tint-amount']}: ${r.toFixed(2)}`);
					}
				}
			}
			expect(failures, failures.join('\n')).toEqual([]);
		});
	});

	it('every section is aliased to a defined hue', () => {
		for (const section of SECTIONS) {
			const alias = CSS.match(new RegExp(`--section-${section}:\\s*var\\(--hue-(\\w+)\\)`));
			expect(alias, `--section-${section} is not aliased to a hue`).not.toBeNull();
			expect(HUES).toContain(alias![1]);
			expect(CSS).toContain(`--section-${section}-soft: var(--hue-${alias![1]}-soft)`);
		}
	});

	it('every section has a data-section rule', () => {
		for (const section of SECTIONS) {
			expect(CSS).toMatch(
				new RegExp(`\\[data-section='${section}'\\] \\{\\s*--section-hue: var\\(--section-${section}\\);`)
			);
		}
	});
});
