// @vitest-environment node
//
// Reads a stylesheet and decodes strings out of it; no DOM, and jsdom costs
// ~690ms of a run this size. See coverComposition.test.ts for the measurement.
import { describe, expect, it } from 'vitest';

import { COVER_STYLE_IDS } from './coverStyles';
import { COVER_CSS_CODE, blocksFor } from '../test/coverCss';

/**
 * The ornaments are SVG documents living inside a CSS file. The ornament
 * section of `cover-type.css` says why they have to be, and that argument is
 * NOT repeated here: it belongs beside the code it justifies, and the first
 * draft of this file duplicated it closely enough to drift within one commit.
 *
 * What the choice costs is what these gate. A drawing is now a percent-encoded
 * string that no editor validates and that fails QUIETLY: one that decodes to
 * nothing renders as empty space, and one whose fill is malformed renders
 * BLACK, which on a dark plate reads as a shadow rather than as a bug. Both of
 * those shipped briefly while these were being drawn, and only a screenshot
 * caught either.
 */
describe('cover ornaments', () => {
	/** The data URIs a single style's own rules draw. Keyed by style rather than
	 *  scanned flat across the file, so a failure names `devotional` instead of
	 *  "ornament 2" — and so the coverage question below can be asked at all. */
	const drawnBy = (style: string) =>
		blocksFor(`.cover-type.style-${style} .rule`)
			.flatMap((m) => [...m[1].matchAll(/url\("data:image\/svg\+xml,([^"]+)"\)/g)])
			.map(([, encoded]) => encoded);

	// Which recipes carry a drawn mark, and — just as deliberately — which do
	// not. `press` is ornamented too but in GRADIENTS, because an angle is two
	// straight lines and two straight lines survive a 48px list row where a
	// curve turns to grey; it therefore has no URI to rot and is bare here.
	const DRAWN = ['devotional', 'revival'];

	it('draws an ornament for exactly the recipes meant to have one', () => {
		for (const style of COVER_STYLE_IDS) {
			expect(
				drawnBy(style).length,
				DRAWN.includes(style)
					? `.style-${style} is meant to carry a drawn ornament and none was found`
					: `.style-${style} is meant to be bare, and something drew one on it`
			).toBe(DRAWN.includes(style) ? 1 : 0);
		}
	});

	it('hides no ornament outside the style blocks', () => {
		// The per-style scan above would report green over a URI that had drifted
		// into some block it does not look at.
		const everywhere = [...COVER_CSS_CODE.matchAll(/url\("data:image\/svg\+xml,/g)];
		expect(
			everywhere.length,
			'a data URI exists that no `.style-* .rule` block owns'
		).toBe(DRAWN.length);
	});

	for (const style of DRAWN) {
		describe(style, () => {
			const encoded = () => {
				const [uri] = drawnBy(style);
				expect(uri, `no ornament for ${style}`).toBeTruthy();
				return uri;
			};
			const svg = () => decodeURIComponent(encoded());

			it('is not double-encoded', () => {
				// `%23fff` run through an encoder that also escapes `%` becomes
				// `%2523fff`, which decodes to the literal text `%23fff` inside the
				// attribute — an invalid colour, which paints black.
				expect(
					encoded(),
					'a `%` is itself encoded, so this decodes to encoded text rather than ' +
						'to markup and the ornament renders wrong or not at all'
				).not.toContain('%25');
			});

			it('decodes to an svg element', () => {
				expect(svg()).toMatch(/^<svg[^>]*\bviewBox=/);
				expect(svg(), 'no xmlns, so the data URI will not parse as SVG').toContain(
					"xmlns='http://www.w3.org/2000/svg'"
				);
				expect(svg().trimEnd()).toMatch(/<\/svg>$/);
			});

			it('names its colour as a keyword, never a hex', () => {
				// A `#` MUST be percent-encoded in a data URI, which is the whole of
				// how the black-fill bug happens, so the drawings simply never carry
				// one. Matched as a hex COLOUR rather than as a bare `#`: an ornament
				// may one day want `url(#…)` for a clipPath or a gradient, and a gate
				// that banned every `#` would fail that with a message about colours.
				expect(
					svg(),
					'a hex colour needs its `#` encoded, which is exactly the mistake that ' +
						'painted an ornament black — use a colour keyword'
				).not.toMatch(/#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})(?![0-9a-fA-F])/);
				expect(svg(), 'nothing sets a fill, so the ornament paints default black').toMatch(
					/fill='(white|none)'/
				);
			});

			it('paints something', () => {
				// An SVG with no drawing at all still decodes, still parses and still
				// renders — as nothing. A `<path>` whose `d` was concatenated as bare
				// path DATA rather than wrapped in an element does exactly that, and
				// it happened here: the revival lozenge silently vanished.
				expect(
					svg(),
					'the document has no drawing elements, so it renders as empty space'
				).toMatch(/<(path|circle|rect|polygon|g)\b/);
				for (const d of [...svg().matchAll(/\bd='([^']*)'/g)].map(([, v]) => v)) {
					expect(d.trim(), 'an empty path').not.toBe('');
					expect(d, 'a path that does not start with a moveto').toMatch(/^\s*[Mm]/);
				}
				// AND NOTHING OUTSIDE AN ELEMENT. Checking that SOME drawing element
				// exists is not enough: the way this actually failed was one `<path>`
				// among several losing its wrapper, leaving `M36 3.4…` as a text node
				// — the other paths still satisfied the check above while the lozenge
				// silently vanished from the render. An ornament is pure markup, so
				// once the tags are removed there must be nothing left at all.
				expect(
					svg().replace(/<[^>]*>/g, '').trim(),
					'text sits between this drawing\'s elements — path data that lost its ' +
						'`<path>` wrapper renders as nothing while the file still looks right'
				).toBe('');
			});
		});
	}
});
