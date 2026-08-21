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

/** Scale a hex colour's channels by `factor` (0–1 darkens, >1 lightens). */
export function shade(hex: string, factor: number): string {
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
 * Legibility floor — the mirror of `ink_safe` in `backend/library/covers.py`.
 *
 * A cover is white type on a coloured plate, and the plate colour is DATA: a
 * hand-picked hex, or one sampled from the English artwork. Nothing between the
 * two ever asked whether white could sit on it, and on 16 covers it couldn't —
 * the 23px author line is not "large text" under WCAG 1.4.3, so AA asks 4.5:1
 * of it and `the-unselfishness-of-god` gave 3.16:1.
 *
 * The backend floors the colour when it draws the file; this floors it the same
 * way when the client draws the fallback, so a book being lazily loaded doesn't
 * flash a plate one shade lighter than the file replacing it.
 * `coverArtParity.test.ts` fails if the two constants drift.
 */
const GRADIENT_END = 0.55;
const AUTHOR_GRADIENT_T = 0.28;
const AUTHOR_INK_OPACITY = 0.86;
const AUTHOR_MIN_CONTRAST = 4.5;

const channels = (hex: string): number[] => {
	const n = (hex || COVER_FALLBACK).replace('#', '');
	const safe = n.length === 6 ? n : COVER_FALLBACK.slice(1);
	return [0, 2, 4].map((i) => parseInt(safe.slice(i, i + 2), 16));
};

/**
 * Scale channels the way the backend's `_darken` does — truncating, where
 * `shade` above rounds. The two differ by at most 1/255, invisible in a
 * gradient, but enough to make the floor below stop one step earlier or later
 * than the backend did and hand one book two subtly different plates.
 */
const scale = (hex: string, factor: number): string =>
	`#${channels(hex)
		.map((c) =>
			Math.max(0, Math.min(255, Math.floor(c * factor)))
				.toString(16)
				.padStart(2, '0')
		)
		.join('')}`;

/** WCAG 2.x relative luminance. */
export function relativeLuminance(hex: string): number {
	const [r, g, b] = channels(hex).map((value) => {
		const c = value / 255;
		return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Contrast of the author line against the plate under it.
 *
 * The byline sits 28% of the way along the plate's gradient, not at its top
 * stop, and the ink is white at 0.86 — both matter by more than the margin
 * between passing and failing.
 */
export function authorInkContrast(hex: string): number {
	const behind = scale(hex, 1 - (1 - GRADIENT_END) * AUTHOR_GRADIENT_T);
	const ink = `#${channels(behind)
		.map((c) =>
			Math.round(AUTHOR_INK_OPACITY * 255 + (1 - AUTHOR_INK_OPACITY) * c)
				.toString(16)
				.padStart(2, '0')
		)
		.join('')}`;
	return (relativeLuminance(ink) + 0.05) / (relativeLuminance(behind) + 0.05);
}

/** The plate colour, darkened just enough to carry white ink at AA. */
export function inkSafe(color: string | null | undefined): string {
	const base = `#${channels(color || COVER_FALLBACK)
		.map((c) => c.toString(16).padStart(2, '0'))
		.join('')}`;
	if (authorInkContrast(base) >= AUTHOR_MIN_CONTRAST) return base;
	// Integer steps, matching the backend's ladder exactly (see ink_safe).
	for (let step = 99; step > 0; step--) {
		const candidate = scale(base, step / 100);
		if (authorInkContrast(candidate) >= AUTHOR_MIN_CONTRAST) return candidate;
	}
	return '#000000'; // unreachable: black passes at 21:1
}

/**
 * The cover gradient: the book's colour, falling to a darker tone of itself.
 * `0.55` is the same factor `generate_covers` bakes into the real artwork, so a
 * generated cover and this fallback sit at the same value.
 */
export function coverGradient(color: string | null | undefined): string {
	const base = inkSafe(color);
	return `linear-gradient(150deg, ${base} 0%, ${shade(base, GRADIENT_END)} 100%)`;
}
