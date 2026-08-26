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
 *
 * It has since become the app's home for colour ARITHMETIC generally — parsing,
 * scaling, and moving a hue into a usable range — for the same reason it was
 * written: that maths had been spelled four different ways in four files. A new
 * helper of that kind belongs here rather than in the component that needs it.
 */

/** The generator's default cover colour, for books with no `cover_color`. */
const COVER_FALLBACK = '#3b5bdb';

/**
 * The [r, g, b] of a `#rrggbb` colour, 0–255.
 *
 * Exported because the one-line parse was being retyped wherever a colour had
 * to be taken apart — `shade` below, the emblem accent derivation, the share
 * card's contrast floor — and only this copy ever had the malformed-input
 * guard, so the others quietly returned NaN channels on a bad hex.
 */
export function channels(hex: string): [number, number, number] {
	const n = (hex || COVER_FALLBACK).replace('#', '');
	const src = n.length === 6 ? n : COVER_FALLBACK.slice(1);
	return [0, 2, 4].map((i) => parseInt(src.slice(i, i + 2), 16)) as [number, number, number];
}

/** The inverse of `channels` — rounds and clamps, so callers can pass floats. */
export function toHex(rgb: number[]): string {
	return `#${rgb
		.map((c) =>
			Math.max(0, Math.min(255, Math.round(c)))
				.toString(16)
				.padStart(2, '0')
		)
		.join('')}`;
}

/**
 * Scale a hex colour's channels by `factor` (0–1 darkens, >1 lightens).
 *
 * Module-private, like `COVER_FALLBACK`: `coverGradient` is the whole public
 * surface for the fallback plate. A malformed `cover_color` (it is an
 * unvalidated CharField) returns the fallback UNSCALED, as it always has —
 * darkening it instead would change what a broken row looks like.
 */
function shade(hex: string, factor: number): string {
	const n = (hex || COVER_FALLBACK).replace('#', '');
	if (n.length !== 6) return COVER_FALLBACK;
	return toHex(channels(hex).map((c) => c * factor));
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
 * A cover under `/covers/` ending `.svg` is a plate GROUND: the book's colour,
 * the vignette and its topic emblem, and no words at all — `BookCover` sets the
 * edition's title over it, exactly as it does over a painting.
 *
 * The words used to be IN this file, and moving them out is what let a cover be
 * set in a webfont: an SVG served through `<img>` renders in a document that
 * cannot reach the page's fonts, so every generated cover in the library came
 * out in Georgia. See `$lib/coverStyles`.
 *
 * The extension is the whole test, and it is the same one `generate_covers`
 * uses to decide what it may redraw (`is_generated`). A `.jpg`/`.png` under
 * `/covers/` is a DESIGNED cover with its type baked in — drawing a second
 * title over those would be the mess this distinguishes.
 *
 * Still per-(slug, language) on disk, and no longer needs to be: a ground with
 * no words in it is language-neutral, like the paintings, so the eight copies
 * of each are eight identical files. Consolidating them means repointing every
 * translated row's `cover_url`, which is a fixture change and its own PR.
 */
export function isPlateCover(url: string | null | undefined): boolean {
	return (url ?? '').startsWith('/covers/') && url!.endsWith('.svg');
}

/**
 * The webp variant files beside a raster cover; empty when there are none.
 *
 * A generated plate is a few KB of vector with nothing to resize, so it gets no
 * variants and must not claim any — and the same goes for anything outside
 * `/covers/`. That scope is load-bearing rather than tidiness: a srcset
 * candidate that 404s renders a BROKEN image (with an explicit `1x` the browser
 * never falls back to `src`), `build_cover_assets.py` walks book editions
 * alone, and search paints author portraits (`/portraits/<slug>.jpg`) through
 * this same helper while an admin may paste an external cover URL. Neither has
 * variants, and neither has BookCover's onerror plate to catch it. Promise only
 * what the builder actually writes.
 *
 * Two callers, which is why this returns the files rather than the markup:
 * `coverSrcset` renders them, and the offline download precaches them (the
 * browser asks for a variant, never the original, so caching `cover_url` alone
 * left a downloaded book coverless after the next deploy).
 */
export function coverVariants(url: string | null | undefined): string[] {
	if (!url?.startsWith('/covers/') || !RASTER.test(url)) return [];
	const base = url.replace(RASTER, '');
	return COVER_WIDTHS.map((w) => `${base}-${w}.webp`);
}

/**
 * Those variants as a `srcset`; '' when there are none to offer.
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
	return coverVariants(url)
		.map((file, i) => `${file} ${i + 1}x`)
		.join(', ');
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
const GROUND_RIB = 0.959;

export function coverGradient(color: string | null | undefined): string {
	// Both stops go through `shade`, which returns the fallback for anything that
	// isn't a six-digit hex. `cover_color` is a free-text CharField the admin
	// import can set, and this string lands in a `style` attribute — an unchecked
	// value could carry a `;` and a second declaration into it.
	// `GROUND_RIB` is the real plate's ribbing, averaged. `covers.build_ground`
	// lays a black rib over its gradient — 1.5 of every 4 user units at alpha
	// 0.11 — which multiplies the whole plate by 1 - (1.5/4 x 0.11) = 0.959.
	// The rib itself is NOT restated here and should not be: its period is in the
	// file's user units, so at the 2.5rem these fans draw at it is a quarter of a
	// pixel wide and averages away to exactly this darkening. What would be wrong
	// is leaving it out, which is the failure the note below already describes —
	// a fallback lighter than the artwork quietly spends `ink_safe`'s margin.
	// Measured against the rendered plates rather than taken from the algebra:
	// 0.9590-0.9596 across four books, against 0.9587 predicted.
	const base = shade(color ?? '', GROUND_RIB);
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

/**
 * The same colour, moved into a lightness band that actually tints.
 *
 * A hue used through `color-mix` at single-digit percentages contributes
 * almost nothing when it is very dark: the raven emblem's slate (#273748,
 * lightness 0.22) mixed at 9% left its sermon plate looking untinted in dark
 * mode while every other sermon wore a visible wash — one sermon looking like
 * the feature was broken.
 *
 * `emblemHue` deliberately does NOT do this, because how light a hue needs to
 * be depends on the surface it lands on, which the catalogue cannot know. This
 * is the app-side half of that split (the share card's half is
 * `scripts/og-card.mjs:liftToContrast`, which solves the opposite problem —
 * type ON the hue rather than a wash OF it).
 *
 * `covers.py:palette_from_artwork` floors a colour sampled off artwork for the
 * same REASON — a hue picked from a drawing arrives at whatever lightness the
 * drawing used, and everything downstream assumes a usable one — though not to
 * the same numbers: its 0.30-0.46 is tuned for type on a plate, this for a wash
 * under one. Hue and saturation are untouched, so a lifted slate still reads as
 * that emblem's slate.
 *
 * The band is fixed rather than measured against the surface, unlike its
 * counterpart on the share card. A plate has to work in light AND dark from one
 * value, so this is the mid-tone intersection that survives both grounds — not
 * a theme-aware calculation, and it should not be mistaken for one.
 */
export function tintable(hex: string, min = 0.34, max = 0.52): string {
	const rgb = channels(hex);
	const lightness = (Math.max(...rgb) + Math.min(...rgb)) / 510;
	const target = Math.min(Math.max(lightness, min), max);
	if (target === lightness) return toHex(rgb);
	// Scaled about the end it is heading for rather than about zero: pushing
	// toward white going up and toward black going down keeps the saturation the
	// eye reads, where a flat multiply washes a light colour out as it climbs.
	// (Going down that IS a flat multiply, which is exactly `shade`.)
	if (target < lightness) return shade(toHex(rgb), target / lightness);
	const scale = (1 - target) / (1 - lightness);
	return toHex(rgb.map((c) => 255 - (255 - c) * scale));
}

/**
 * WCAG relative luminance of an [r, g, b], 0–1.
 *
 * Here rather than beside its caller because this module's header already
 * claims colour ARITHMETIC generally, and a constant like 0.03928 typed out per
 * call site is one that gets corrected in a single place and stays wrong in the
 * others.
 *
 * TWO OTHER COPIES SURVIVE, both for a reason. `covers.py` cannot import
 * anything under `frontend/` — the API image is built from `backend/` alone.
 * And `scripts/og-card.mjs` could import this, but `sermonCards.test.ts`
 * digests that file's SOURCE to catch composition drift, so even a
 * behaviour-preserving edit demands every sermon card be redrawn — and those
 * can only be drawn on Linux, since the generator wants the Liberation faces.
 * Deduplicating it needs to be done from a machine that can re-run
 * `npm run og:sermons`, not from here.
 */
export function relativeLuminance(rgb: number[]): number {
	const [r, g, b] = rgb.map((value) => {
		const c = value / 255;
		return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG contrast ratio between two [r, g, b] colours — 1 (same) to 21. */
export function contrastRatio(a: number[], b: number[]): number {
	const [hi, lo] = [relativeLuminance(a), relativeLuminance(b)].sort((x, y) => y - x);
	return (hi + 0.05) / (lo + 0.05);
}
