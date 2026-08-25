import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { CARD_SERIF, SCRIPT_FACE, quoteStyle } from './quoteCard';

const APP_CSS = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8').replace(
	/\/\*[\s\S]*?\*\//g,
	''
);

/**
 * The quote card is the one place a `var()` cannot reach.
 *
 * `ctx.font` takes a plain font shorthand, so the canvas has to restate the
 * stack that every other surface names as `--font-display`. That copy is the
 * risk these gate: the card draws the reader's own selected sentence and is
 * built to leave the site, so a drift here ships as a PNG in the wrong face,
 * on someone else's timeline, permanently.
 */
describe('quote card type', () => {
	const families = (value: string) => [...value.matchAll(/'([^']+)'/g)].map(([, f]) => f);

	it('names the same faces app.css does', () => {
		const at = APP_CSS.indexOf('--font-display:');
		const token = families(APP_CSS.slice(at, APP_CSS.indexOf(';', at)));
		expect(token.length, '--font-display names no families').toBeGreaterThan(0);
		expect(
			families(CARD_SERIF),
			'the canvas stack has drifted from --font-display — a quote card would ship ' +
				'in a different face from the chapter it was taken out of'
		).toEqual(token);
	});

	/** Is this family a webfont the app ships, or a device face like Georgia? */
	const isWebfont = (family: string) => {
		const slug = family
			.replace(/ Variable$/, '')
			.toLowerCase()
			.replace(/ /g, '-');
		return ['@fontsource-variable', '@fontsource'].some((scope) =>
			existsSync(join(process.cwd(), 'node_modules', scope, slug))
		);
	};

	it('preloads a face for every script the stack can reach', () => {
		// `ctx.fillText` does not wait for a webfont the way the DOM does: it
		// silently paints the fallback, and the PNG keeps it. So every non-Latin
		// WEBFONT the stack names has to be loaded before the canvas draws —
		// Georgia and Times New Roman are the device tail and need nothing.
		for (const family of families(CARD_SERIF).slice(1).filter(isWebfont)) {
			expect(
				Object.values(SCRIPT_FACE),
				`${family} is in the canvas stack but nothing preloads it, so a card in ` +
					`that script draws in the device font before it arrives`
			).toContain(family);
		}
	});

	it('asks a script face only for what it has', () => {
		// The Latin card is `italic 600`. Amiri and Tiro have no italic at all and
		// Amiri ships 400 and 700 with nothing between, so the Latin style asked
		// all three for two things they have not got — a synthesised slant over a
		// synthesised bold, baked into a shareable image.
		expect(quoteStyle(null), 'Latin should keep its italic').toBe('italic 600');
		for (const script of ['arabic', 'devanagari', 'cyrillic']) {
			const style = quoteStyle(script);
			expect(style, `${script} would get a faked italic`).not.toContain('italic');
			expect(style, `${script} would get a synthesised weight`).toBe('400');
		}
	});
});
