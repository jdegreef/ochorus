// @vitest-environment node
//
// This file reads a stylesheet and matches regexes against it; it touches no
// DOM. `vitest.config.ts` sets jsdom globally, and standing one up costs ~690ms
// of a ~990ms run here — measured. Opting out takes the file to ~250ms and
// frees a jsdom instance in CI's per-file worker pool.
import { describe, expect, it } from 'vitest';

import { COVER_STYLE_IDS, CURSIVE_SCRIPTS } from './coverStyles';
import { COVER_CSS, blocksFor } from '../test/coverCss';

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
	/** Every rule the CSS writes for one style, whatever it targets.
	 *
	 *  ANCHORED TO THE START OF A LINE and stopped at one, because a selector is
	 *  the only thing that starts a line here. Unanchored, this scraped the PROSE:
	 *  the comment that mentions `.cover-type.style-press .title` came back as a
	 *  rule target, which would let a style satisfy "has a composition" with a
	 *  sentence about one, and would fail the edges gate the day a comment named
	 *  `.byline`. */
	const rulesFor = (style: string) =>
		[
			...COVER_CSS.matchAll(
				new RegExp(`^\\s*\\.cover-type\\.style-${style}([^{,\\n]*)[,{]`, 'gm')
			)
		].map(([, target]) => target.trim());

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
		// Detected with the shared scanner, which follows a selector through a
		// GROUP. The three compositions share one tracked-caps block, and only the
		// last selector in that group is the one followed by `{` — a regex demanding
		// `.style-<id> .subtitle {` therefore saw `revival` alone and would have let
		// a change to `press` or `inscriptional` past.
		const tracked = COVER_STYLE_IDS.filter((style) =>
			blocksFor(`.cover-type.style-${style} .subtitle`).some((m) =>
				/letter-spacing:\s*[.\d]/.test(m[1])
			)
		);
		expect(
			tracked.length,
			'no composition tracks a subtitle; this gate is watching nothing'
		).toBeGreaterThan(1);

		// The LAST rule wins: every selector here is three classes by construction,
		// so nothing but source order decides. Both offsets are taken from the same
		// comment-stripped text — mixing a stripped index with a raw one compares
		// two different coordinate systems and silently drifts by the length of
		// every comment between them.
		const lastTracking = Math.max(
			...tracked.flatMap((style) =>
				blocksFor(`.cover-type.style-${style} .subtitle`).map((m) => m.index!)
			)
		);
		for (const script of CURSIVE_SCRIPTS) {
			// Two `.script-<x> .subtitle` blocks exist — one inside the container
			// gate giving the script its face, one at the foot correcting what a
			// Latin recipe gets wrong — so it is the last that has to do the zeroing,
			// and it has to sit below the composition that set the tracking.
			const blocks = blocksFor(`.cover-type.script-${script} .subtitle`);
			expect(blocks.length, `no .script-${script} .subtitle rule at all`).toBeGreaterThan(0);
			const winner = blocks[blocks.length - 1];
			expect(
				winner[1],
				`${tracked.join(', ')} track the subtitle, and the last .script-${script} ` +
					`rule does not zero it — those covers would have their subtitle torn apart`
			).toMatch(/letter-spacing:\s*0(?![.\d])/);
			expect(
				winner.index!,
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
		// which is what makes a shelf legible as a shelf of different books.
		//
		// SLICED FROM THE GATE ITSELF. This used to find the block's end by
		// searching back from a selector that happens to sit inside it, which
		// landed 73 lines PAST the closing brace — and would have returned -1 the
		// day that selector was renamed, making every assertion below vacuously
		// true while the gate went on reporting green.
		const gate = COVER_CSS.indexOf('@container');
		expect(gate, 'the recipes are no longer behind a container query').toBeGreaterThan(-1);
		const gateBody = COVER_CSS.slice(gate, COVER_CSS.indexOf('\n}\n', gate));
		expect(
			gateBody,
			'a composition sits inside the container gate, so a thumbnail loses its ' +
				'arrangement along with its face'
		).not.toMatch(/\.cover-type\.style-[a-z]+ \.(middle|rule|subtitle)/);
	});

});
