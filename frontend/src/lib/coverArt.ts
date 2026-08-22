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
