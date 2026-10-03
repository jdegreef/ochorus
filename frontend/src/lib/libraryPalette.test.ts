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

/** The declarations of the theme block opened by `selector {` — the one that
 *  sets --bg, since app.css has other bare `:root` blocks (fonts, sections). */
function block(selector: string): Record<string, string> {
	const escaped = selector.replace(/[[\]()]/g, '\\$&');
	const start = CSS.search(new RegExp(`${escaped} \\{\\s*--bg:`));
	if (start === -1) throw new Error(`${selector} theme block not found in app.css`);
	const body = CSS.slice(start, CSS.indexOf('\n}', start));
	const vars: Record<string, string> = {};
	for (const m of body.matchAll(/(--[\w-]+):\s*([^;]+);/g)) vars[m[1]] = m[2].trim();
	return vars;
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
