/**
 * Where a book series' share card lives, per interface language.
 *
 * Not committed: `scripts/build-series-cards.mjs` draws one into the build for
 * every prerendered series page, from the series response that page inlines —
 * its name, promise line, book count and covers, in the page's own language.
 * Said once so the page that names a card and the script that draws it cannot
 * disagree.
 */
export function seriesCardUrl(slug: string, language: string): string {
	return `/og/series/${language}/${slug}.jpg`;
}
