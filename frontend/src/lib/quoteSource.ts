import { i18n } from '$lib/i18n.svelte';

/**
 * A quote's source in prose — "Work, chapter N", or a sermon's title alone —
 * as the copy text, the share card and the /quotes teaser print it. (The card's
 * linked citation is the terser `citeLine` / `citeChapter` form.)
 */

/** ", chapter N" — nothing for a sermon, which has no chapters. */
export const chapterSuffix = (order: number | null): string =>
	order === null ? '' : i18n.t('quotes.clipChapter').replace('%n%', String(order));

export const sourceProse = (src: { work: string; order: number | null }): string =>
	src.work + chapterSuffix(src.order);
