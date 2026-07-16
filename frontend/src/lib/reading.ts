import { i18n } from './i18n.svelte';

/** Estimated reading time in whole minutes from a word count (~200 wpm). */
export function readingMinutes(words: number): number {
	return Math.max(1, Math.round(words / 200));
}

/**
 * Localized reading-time label, e.g. "12 min read" / "dakika 12 za kusoma".
 * The count is substituted into the locale's template so word order stays
 * correct per language (the number isn't always at the front).
 */
export function readingTime(words: number): string {
	const mins = readingMinutes(words);
	// %n%/%h%/%m% (not {n}) so Paraglide doesn't treat these as message params.
	if (mins < 60) return i18n.t('common.minRead').replace('%n%', String(mins));
	const h = Math.floor(mins / 60);
	const m = mins % 60;
	return m
		? i18n.t('common.hrMinRead').replace('%h%', String(h)).replace('%m%', String(m))
		: i18n.t('common.hrRead').replace('%h%', String(h));
}
