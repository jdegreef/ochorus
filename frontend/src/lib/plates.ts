/**
 * A plate's small twin: `/illustrations/<book>/plate-04-….jpg` →
 * `…plate-04-….-320.webp`, drawn beside it by
 * backend/scripts/build_plate_thumbs.py for the series page's row of plates.
 * Null for any other picture, which is then shown as it is.
 */
export function plateThumb(src: string): string | null {
	return /\/[^/]*plate-[^/]*\.jpg$/.test(src) ? src.replace(/\.jpg$/, '-320.webp') : null;
}
