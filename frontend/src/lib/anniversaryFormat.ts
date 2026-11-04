/**
 * A writer's anniversary in the reader's language (AuthorCandle, OnThisDay):
 * kept apart from `$lib/authorDays` so the pages that show one need not load
 * the whole table of days to format it.
 */

/** "13 November 354" — the day as it was, year and all. */
export function anniversaryDate(iso: string, lang: string): string {
	const [y, m, d] = iso.split('-').map(Number);
	// Noon UTC, formatted in UTC: no time zone's historical offset can move
	// the day (and setUTCFullYear, as Date.UTC reads 0–99 as 1900–1999).
	const day = new Date(Date.UTC(2000, m - 1, d, 12));
	day.setUTCFullYear(y);
	return new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(
		day
	);
}

/** "354", in the language's own digits, as the date above writes it. */
export function anniversaryYear(year: number, lang: string): string {
	return new Intl.NumberFormat(lang, { useGrouping: false }).format(year);
}
