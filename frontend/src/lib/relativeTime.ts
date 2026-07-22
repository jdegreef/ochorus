/**
 * A localized "time ago" string via Intl.RelativeTimeFormat, with a caller-
 * supplied "just now" label for the sub-minute case (the util is locale-aware
 * but not i18n-aware — the caller owns message lookup). `now` is injectable so
 * the formatting is deterministic in tests.
 */
export function relativeTime(
	ts: number,
	locale: string,
	justNow: string,
	now: number = Date.now()
): string {
	const diffS = Math.round((ts - now) / 1000);
	if (Math.abs(diffS) < 45) return justNow;
	const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
	const mins = Math.round(diffS / 60);
	if (Math.abs(mins) < 60) return rtf.format(mins, 'minute');
	const hrs = Math.round(diffS / 3600);
	if (Math.abs(hrs) < 24) return rtf.format(hrs, 'hour');
	const days = Math.round(diffS / 86400);
	if (Math.abs(days) < 30) return rtf.format(days, 'day');
	const months = Math.round(diffS / 2592000);
	if (Math.abs(months) < 12) return rtf.format(months, 'month');
	return rtf.format(Math.round(diffS / 31536000), 'year');
}
