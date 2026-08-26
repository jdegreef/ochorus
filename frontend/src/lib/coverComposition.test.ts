import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { COVER_SCRIPTS, COVER_STYLE_IDS } from './coverStyles';

const COVER_CSS = readFileSync(join(process.cwd(), 'src/lib/components/cover-type.css'), 'utf-8');

/**
 * A cover's ARRANGEMENT, not its face.
 *
 * The six recipes used to differ in exactly one way: the typeface of the
 * title. Byline, centred title, short rule, italic subtitle — the same six
 * times, so a shelf read as one publisher's back catalogue set in six fonts.
 * A 1670s title page is not a 1900 one with the font swapped; it is built
 * differently, and `cover-type.css` now builds it differently.
 *
 * These gate what that freedom must not cost: the two edges the composition
 * may not move, a script that tracking would tear apart, and a recipe that
 * quietly goes back to being a face with no arrangement of its own.
 */
describe('cover compositions', () => {
	/** Every rule the CSS writes for one style, whatever it targets. */
	const rulesFor = (style: string) =>
		[...COVER_CSS.matchAll(new RegExp(`\\.cover-type\\.style-${style}([^{,]*)[,{]`, 'g'))].map(
			([, target]) => target.trim()
		);

	it('gives every recipe an arrangement, not only a face', () => {
		// The defect this whole section exists to fix. A style whose only rule
		// targets `.title` is a font swap wearing the same layout as the five
		// beside it — which is what all six were.
		for (const style of COVER_STYLE_IDS) {
			const beyondTheTitle = rulesFor(style).filter((t) => t !== '.title' && t !== '');
			expect(
				beyondTheTitle.length,
				`.style-${style} only ever sets .title, so it is a face with no composition ` +
					`of its own — the thing this section was written to end`
			).toBeGreaterThan(0);
		}
	});

	it('never tracks a subtitle in a cursive script', () => {
		// Three compositions set the subtitle in tracked capitals — the small-caps
		// line a period title page puts under its title. Tracking is what prises
		// Arabic's joins apart and breaks Devanagari's conjuncts, and the title has
		// been corrected for it since those scripts got faces; the subtitle had
		// never needed it before these arrangements existed. One live cover sits on
		// this: `the-way-to-god` in Arabic is a `revival` book with a real Arabic
		// subtitle.
		const tracked = COVER_STYLE_IDS.filter((style) =>
			new RegExp(`\\.cover-type\\.style-${style} \\.subtitle \\{[^}]*letter-spacing:\\s*[.\\d]`)
				.test(COVER_CSS)
		);
		expect(tracked.length, 'no composition tracks a subtitle; this gate is watching nothing')
			.toBeGreaterThan(0);
		for (const script of ['arabic', 'devanagari']) {
			// There are TWO `.script-<x> .subtitle` blocks — one inside the
			// container gate giving the script its face, one at the foot correcting
			// what a Latin recipe gets wrong. Both are three classes, exactly like
			// the style blocks, so nothing but SOURCE ORDER decides which wins:
			// the correction has to zero the tracking AND sit after the composition
			// that set it. Checking the first block found would pass on the wrong
			// one, which is what this gate did before it was fixed.
			const zeroed = [
				...COVER_CSS.matchAll(
					new RegExp(`\\.cover-type\\.script-${script} \\.subtitle[^{]*\\{([^}]*)\\}`, 'g')
				)
			].filter((m) => /letter-spacing:\s*0(?![.\d])/.test(m[1]));
			expect(
				zeroed.length,
				`${tracked.join(', ')} track the subtitle, and no .script-${script} rule ` +
					`zeroes it — those covers would have their subtitle torn apart`
			).toBeGreaterThan(0);

			const lastTracking = Math.max(
				...tracked.map((style) =>
					COVER_CSS.search(new RegExp(`\\.cover-type\\.style-${style} \\.subtitle \\{`))
				)
			);
			expect(
				zeroed[zeroed.length - 1].index!,
				`the ${script} correction sits above the compositions that track the ` +
					`subtitle, so it loses the cascade and does nothing`
			).toBeGreaterThan(lastTracking);
		}
	});

	it('leaves the two edges the renderers agree on alone', () => {
		// The composition owns `.middle` and nothing else. The byline's height is
		// where `covers.ink_safe` floors a plate's colour for contrast, and the
		// foot is what `coverBand.test.ts` pins against covers.py — two renderers
		// and a contrast guarantee meet at those edges. A style that moved either
		// would break a promise made in Python.
		for (const style of COVER_STYLE_IDS) {
			for (const target of rulesFor(style)) {
				expect(
					target,
					`.style-${style} styles ${target}, which is one of the edges covers.py ` +
						`also draws to — move it and the two renderers disagree`
				).not.toMatch(/\.byline|\.emblem-band|\.brandmark/);
			}
			expect(
				new RegExp(`\\.cover-type\\.style-${style} \\{[^}]*padding`).test(COVER_CSS),
				`.style-${style} sets its own padding, which moves the byline off the ` +
					`height ink_safe floored the colour against`
			).toBe(false);
		}
	});

	it('keeps the arrangements out of the container gate', () => {
		// The gate exists so a 48px thumbnail does not FETCH a display face it
		// cannot show. An ornament fetches nothing and is drawn to read small, so
		// a thumbnail keeps its composition even where it does not get its face —
		// which is what makes the shelf legible as a shelf of different books.
		const gate = COVER_CSS.indexOf('@container');
		expect(gate, 'the recipes are no longer behind a container query').toBeGreaterThan(-1);
		const gateEnd = COVER_CSS.indexOf('\n}\n', COVER_CSS.lastIndexOf('.cover-type.script-cyrillic.style-inscriptional'));
		for (const style of COVER_STYLE_IDS) {
			for (const m of COVER_CSS.matchAll(
				new RegExp(`\\.cover-type\\.style-${style} \\.(middle|rule|subtitle)`, 'g')
			)) {
				expect(
					m.index! > gate && m.index! < gateEnd,
					`.style-${style} arranges ${m[1]} inside the container gate, so a ` +
						`thumbnail loses its composition`
				).toBe(false);
			}
		}
	});

	it('corrects every script the library is read in', () => {
		// A guard on the guard: the tracking correction above names two scripts by
		// hand. If a fourth script is ever added to COVER_SCRIPTS, this says so
		// rather than letting it inherit a Latin arrangement silently.
		expect([...COVER_SCRIPTS].sort()).toEqual(['arabic', 'cyrillic', 'devanagari']);
	});
});
