/**
 * The generated-cover fallback, in one place.
 *
 * Roughly half the library ships without artwork, so what a cover-less book
 * looks like is a real surface, not an edge case — and it was drawn four
 * different ways: a flat fill on the plans strip, a `…, #0008` gradient on the
 * book page, a local `cover()`/`shade()` pair on the 404, and a `darken(0.55)`
 * inside BookCover. The same book therefore looked different on the shelf, on
 * its own page and on the error page, and the brand blue was hardcoded in five
 * files.
 *
 * A book's own `cover_color` is data, not a UI colour (STYLE_GUIDE §1), which
 * is why it is a raw hex rather than a token. Only the DEFAULT belongs here.
 *
 * hex-ok-file: the constant below IS that default — the colour a book wears
 * when the data has none. It is a stand-in for a data value, not a surface, so
 * it must not follow the reader's theme.
 */

/** The generator's default cover colour, for books with no `cover_color`. */
export const COVER_FALLBACK = '#3b5bdb';

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

/** Scale a hex colour's channels by `factor` (0–1 darkens, >1 lightens). */
export function shade(hex: string, factor: number): string {
	// A malformed `cover_color` (it is an unvalidated CharField) returns the
	// fallback UNSCALED, as it always has — darkening it instead would change
	// what a broken row looks like, which is not this refactor's business.
	const n = (hex || COVER_FALLBACK).replace('#', '');
	if (n.length !== 6) return COVER_FALLBACK;
	return toHex(channels(hex).map((c) => c * factor));
}

/**
 * The cover gradient: the book's colour, falling to a darker tone of itself.
 * `0.55` is the same factor `generate_covers` bakes into the real artwork, so a
 * generated cover and this fallback sit at the same value.
 */
export function coverGradient(color: string | null | undefined): string {
	const base = color || COVER_FALLBACK;
	return `linear-gradient(150deg, ${base} 0%, ${shade(base, 0.55)} 100%)`;
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
 * The band is `covers.py:palette_from_artwork`'s, which floors a colour sampled
 * off artwork for the same reason: a hue picked from a drawing arrives at
 * whatever lightness the drawing used, and the treatment downstream assumes a
 * usable one. Hue and saturation are untouched, so a lifted slate is still that
 * emblem's slate.
 */
export function tintable(hex: string, min = 0.34, max = 0.52): string {
	const [r, g, b] = channels(hex).map((c) => c / 255);
	const hi = Math.max(r, g, b);
	const lo = Math.min(r, g, b);
	const lightness = (hi + lo) / 2;
	const target = Math.min(Math.max(lightness, min), max);
	if (target === lightness || hi === lo) return toHex(channels(hex));
	// Scaled about the ends rather than about the midpoint: pushing toward white
	// above 0.5 and toward black below keeps the saturation the eye reads, where
	// a flat multiply washes a light colour out as it climbs.
	const scale = target > lightness ? (1 - target) / (1 - lightness) : target / lightness;
	return toHex(
		channels(hex).map((c) =>
			target > lightness ? 255 - (255 - c) * scale : c * scale
		)
	);
}
