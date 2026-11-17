import { COVER_WIDTHS } from './coverArt';

/**
 * A plate's webp variants: `/illustrations/<book>/plate-04-….jpg` →
 * `…plate-04-…-320.webp` and `-640.webp`, drawn beside it by
 * backend/scripts/build_plate_thumbs.py (the covers' `write_variants`, so the
 * covers' widths) for the series page's row of plates. Empty for any other
 * picture, which is then shown as it is.
 */
export function plateVariants(src: string): string[] {
	if (!/\/[^/]*plate-[^/]*\.jpg$/.test(src)) return [];
	const base = src.replace(/\.jpg$/, '');
	return COVER_WIDTHS.map((w) => `${base}-${w}.webp`);
}

/** Those variants at 1x and 2x — density, not width, descriptors, as
 *  `coverSrcset` explains — or '' for a picture with none. */
export const plateSrcset = (src: string): string =>
	plateVariants(src)
		.map((file, i) => `${file} ${i + 1}x`)
		.join(', ');
