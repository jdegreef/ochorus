/**
 * The generated-cover fallback, in one place.
 *
 * Every published book now carries a committed cover (two fixture gates keep it
 * that way), so a cover-less book is the admin import before its file is drawn,
 * the unpublished draft, and the broken image. It was once half the library,
 * and it was drawn four different ways: a flat fill on the plans strip, a
 * `…, #0008` gradient on the book page, a local `cover()`/`shade()` pair on the
 * 404, and a `darken(0.55)` inside BookCover. The same book therefore looked
 * different on the shelf, on its own page and on the error page, and the brand
 * blue was hardcoded in five files.
 *
 * A book's own `cover_color` is data, not a UI colour (STYLE_GUIDE §1), which
 * is why it is a raw hex rather than a token. Only the DEFAULT belongs here.
 *
 * hex-ok-file: the constant below IS that default — the colour a book wears
 * when the data has none. It is a stand-in for a data value, not a surface, so
 * it must not follow the reader's theme.
 */

/** The generator's default cover colour, for books with no `cover_color`. */
const COVER_FALLBACK = '#3b5bdb';

/** Scale a hex colour's channels by `factor` (0–1 darkens, >1 lightens). */
function shade(hex: string, factor: number): string {
	const n = (hex || COVER_FALLBACK).replace('#', '');
	if (n.length !== 6) return COVER_FALLBACK;
	const channels = [0, 2, 4].map((i) =>
		Math.max(0, Math.min(255, Math.round(parseInt(n.slice(i, i + 2), 16) * factor)))
			.toString(16)
			.padStart(2, '0')
	);
	return `#${channels.join('')}`;
}

/**
 * The widths every raster cover is built at, and how a variant is named.
 * `backend/scripts/build_cover_assets.py` writes them and a fixture gate proves
 * they exist, so `srcset` here is a promise something keeps.
 */
export const COVER_WIDTHS = [320, 640];
const RASTER = /\.(jpe?g|png)$/;

/**
 * A cover under `covers/art/` is a PAINTING, not a finished cover: one file per
 * work, shared by every language, with the title drawn over it. It carries no
 * words, which is why it needs no translation — and why it cannot stand in as
 * an og:image, where a preview card is often all a reader sees.
 */
export function isArtCover(url: string | null | undefined): boolean {
	return (url ?? '').startsWith('/covers/art/');
}

/**
 * The webp variants beside a raster cover, as a `srcset`; '' when there are
 * none to offer. A generated plate is a few KB of vector with nothing to
 * resize, so it gets no variants and must not claim any.
 *
 * Lives here rather than in BookCover because the small fans — CoverStrip,
 * ShelfCard, ContinueReading — draw covers at 2.5rem WITHOUT that component,
 * and were fetching 397 KB PNGs to paint 40 pixels.
 *
 * DENSITY descriptors (`1x`/`2x`), not width descriptors. A `w` descriptor is a
 * claim about the file's real pixel width, and the builder never upscales — so
 * `godliness-640.webp` is actually 424px wide and `640w` would be a lie the
 * browser makes selection decisions on. Every cover is painted in a box whose
 * CSS size the layout already fixes (40px in a fan, 128px beside a book's
 * details), which is exactly the case `x` descriptors describe: no `sizes` to
 * keep in step with the CSS, and nothing claimed that isn't true.
 */
export function coverSrcset(url: string | null | undefined): string {
	if (!url || !RASTER.test(url)) return '';
	const base = url.replace(RASTER, '');
	return COVER_WIDTHS.map((w, i) => `${base}-${w}.webp ${i + 1}x`).join(', ');
}

/**
 * The cover gradient: the book's colour, falling to a darker tone of itself.
 *
 * This is the WHOLE treatment for the small decorative fans — `CoverStrip`,
 * `ShelfCard`, `ContinueReading`. They render at 2.5rem, where the plate's type
 * would be sub-pixel, and they hold a `TopicCover` (title, url, colour) rather
 * than a book, so routing them through `BookCover` would mean widening that
 * type at every call site to draw something nobody can read. Deliberate, not an
 * oversight.
 * `0.55` is the same factor `generate_covers` bakes into the real artwork, so a
 * generated cover and this fallback sit at the same value.
 */
export function coverGradient(color: string | null | undefined): string {
	// Both stops go through `shade`, which returns the fallback for anything that
	// isn't a six-digit hex. `cover_color` is a free-text CharField the admin
	// import can set, and this string lands in a `style` attribute — an unchecked
	// value could carry a `;` and a second declaration into it.
	const base = shade(color ?? '', 1);
	// `165deg … 89%` is covers.py's gradient written in CSS, not an eyeball
	// match. The file runs its gradient from (0, 0) to (0.35, 1) in bounding-box
	// units — on a 600x800 plate a vector of (210, 800), atan(210/800) off
	// vertical, i.e. 165deg — and SVG PADS past its end point while CSS stretches
	// its gradient line corner to corner. Projecting the file's end point onto
	// that line puts it at 89.3% along, so the dark stop goes there; left at 100%
	// the whole plate sits lighter than the artwork it stands in for.
	//
	// Not only cosmetic. `covers.ink_safe` floors a plate colour against the tone
	// under the byline in the FILE'S geometry, so a lighter gradient here quietly
	// spends that margin: at the old `150deg … 100%` the byline measured 4.37:1
	// against a 4.5 bar.
	return `linear-gradient(165deg, ${base} 0%, ${shade(base, 0.55)} 89%)`;
}
