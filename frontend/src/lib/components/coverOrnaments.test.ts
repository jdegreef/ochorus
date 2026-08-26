// @vitest-environment node
//
// Reads a stylesheet and decodes strings out of it; no DOM, and jsdom costs
// ~690ms of a run this size. See coverComposition.test.ts for the measurement.
import { describe, expect, it } from 'vitest';

import { COVER_CSS_CODE } from '../../test/coverCss';

/**
 * The ornaments, which are SVG documents living inside a CSS file.
 *
 * That is not a stylistic choice. `generate-cover-og.mjs` renders the share
 * card with `page.setContent` — no server and no document base — so a
 * `url(/ornaments/…)` would resolve to nothing there while looking perfect in
 * the app, and an ornament added as an ELEMENT would have to be added twice,
 * once in the component and once in that script's hand-built markup, with
 * nothing gating the two copies against each other.
 *
 * The cost of that choice is that a drawing is now a percent-encoded string
 * which no editor validates and which fails QUIETLY: an ornament that decodes
 * to nothing renders as empty space, and one whose fill is malformed renders
 * BLACK, which on a dark plate looks like a shadow rather than like a bug.
 * Both of those happened here. These decode every URI and fail loudly instead.
 */
describe('cover ornaments', () => {
	const uris = [...COVER_CSS_CODE.matchAll(/url\("data:image\/svg\+xml,([^"]+)"\)/g)].map(
		([, encoded]) => encoded
	);

	it('finds both of the drawn ornaments', () => {
		// Everything below is `for (const …)`, so an encoding change that stopped
		// matching would leave this file reporting green over nothing at all.
		//
		// TWO, not three: `press`'s corner pieces are gradients rather than a
		// drawing, deliberately — an angle is two straight lines, and two straight
		// lines survive a 64px thumbnail where a curve turns to grey. Only the
		// quatrefoil and the centre-piece are SVG, so only they can rot this way.
		expect(uris.length, 'no data-URI ornaments found; this file is watching nothing').toBe(2);
	});

	for (const [i, encoded] of uris.entries()) {
		describe(`ornament ${i + 1}`, () => {
			const svg = decodeURIComponent(encoded);

			it('is not double-encoded', () => {
				// `%23fff` run through an encoder that also escapes `%` becomes
				// `%2523fff`, which decodes to the literal text `%23fff` inside the
				// attribute — an invalid colour, which paints black.
				expect(
					encoded,
					'a `%` is itself encoded, so this URI decodes to encoded text rather ' +
						'than to markup — the ornament will render wrong or not at all'
				).not.toContain('%25');
			});

			it('decodes to an svg element', () => {
				expect(svg).toMatch(/^<svg[^>]*\bviewBox=/);
				expect(svg, 'no xmlns, so a data URI will not parse as SVG').toContain(
					"xmlns='http://www.w3.org/2000/svg'"
				);
				expect(svg.trimEnd()).toMatch(/<\/svg>$/);
			});

			it('names its colour as a keyword, never a hex', () => {
				// A `#` MUST be percent-encoded in a data URI, which is the whole of
				// how the black-fill bug happens. A keyword has no such edge, so the
				// rule here is that the drawings simply never contain one.
				expect(
					svg,
					'a hex colour needs its `#` encoded, which is exactly the mistake that ' +
						'painted an ornament black — use a colour keyword'
				).not.toContain('#');
				expect(svg, 'nothing sets a fill, so the ornament paints default black').toMatch(
					/fill='(white|none)'/
				);
			});

			it('paints something', () => {
				// An SVG with no drawing at all still decodes, still parses, and still
				// renders — as nothing. A `<path>` whose `d` was concatenated as bare
				// path DATA rather than wrapped in an element does exactly this, and
				// it happened while these were being drawn.
				expect(
					svg,
					'the document has no drawing elements, so it renders as empty space'
				).toMatch(/<(path|circle|rect|polygon|g)\b/);
				for (const d of [...svg.matchAll(/\bd='([^']*)'/g)].map(([, v]) => v)) {
					expect(d.trim(), 'an empty path').not.toBe('');
					expect(d, 'a path that does not start with a moveto').toMatch(/^\s*[Mm]/);
				}
			});
		});
	}
});
