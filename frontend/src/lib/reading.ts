import { i18n } from './i18n.svelte';

/** Estimated reading time in whole minutes from a word count (~200 wpm). */
export function readingMinutes(words: number): number {
	return Math.max(1, Math.round(words / 200));
}

/**
 * Whole minutes of reading left, from a word count and how far through the
 * reader is (0-1).
 *
 * Floored at 1: the chapter reader used a bare Math.ceil, so the foot of a
 * chapter read "0 min left" — which is not a reading time, and disagreed with
 * the sermon page, which floored at 1 in its own private copy. Shared so the two
 * surfaces cannot drift again.
 */
export function minutesLeft(words: number, frac: number): number {
	return Math.max(1, Math.ceil(readingMinutes(words) * (1 - Math.min(1, Math.max(0, frac)))));
}

/**
 * Book-progress percent for the "Continue reading" card, from the chapter
 * currently open (`order`, 1-based) and the book's chapter count.
 *
 * The current chapter is treated as half-read (a midpoint estimate — we know
 * which chapter is open but not how far through it), so the value never reads
 * 0% for someone on chapter 1, never counts the open chapter as fully finished,
 * and stays below 100% until the whole book is genuinely done. Clamped to
 * [1, 99] so the bar is always visibly started and never claims completion.
 */
export function bookProgressPercent(order: number, chapterCount: number): number {
	if (chapterCount <= 0) return 0;
	const raw = ((order - 0.5) / chapterCount) * 100;
	return Math.min(99, Math.max(1, Math.round(raw)));
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

/**
 * The year a sermon was preached, for display — `''` when undated (about half
 * the shelf). Shared so the sermon shelf and the sermon page agree on both the
 * slice and the empty-string fallback; they had grown identical private copies.
 */
export function preachedYear(preachedOn: string | null): string {
	return preachedOn?.slice(0, 4) ?? '';
}

/**
 * Height of the reader's sticky top bar, and so the line every "which
 * paragraph is at the top of the screen" question is measured against —
 * scroll anchors, read-aloud's starting paragraph, the sermon outline's
 * active section.
 *
 * Shared because it had already drifted: the reader and the sermon page each
 * held 64 while the chapter reader held 72, so the same scroll produced two
 * different answers about where the reader was.
 */
export const HEADER_OFFSET = 64;

/**
 * A content-language code as a `lang` attribute value.
 *
 * Reading surfaces never set `lang` on the prose, so the browser fell back to
 * the document's language — which is the UI LOCALE, not the content's. Those
 * routinely differ: an English book read under `/ar`, a Swahili sermon opened
 * from an English browse page. That is invisible until a reader justifies the
 * text, at which point `hyphens: auto` consults the wrong dictionary (or none)
 * and the prose fills with rivers.
 *
 * `en-modern` is our own edition marker, not a real subtag, so it is reduced to
 * its base language — a Modern English edition hyphenates as English.
 */
export function contentLang(language: string): string {
	return language === 'en-modern' ? 'en' : language;
}


/**
 * Keep a centred popover inside the viewport.
 *
 * The scripture and definition popovers are positioned at the tapped word and
 * centred on it with `translate(-50%)`, at a fixed width — so a reference near
 * either margin rendered half off-screen, which on a phone is most of them.
 * Callers pass the word's centre in PAGE coordinates; the clamp is done in
 * VIEWPORT coordinates and converted back, since the viewport is what the
 * popover has to fit inside.
 */
export function clampPopoverLeft(pageLeft: number, width: number, gutter = 12): number {
	if (typeof window === 'undefined') return pageLeft;
	const half = Math.min(width, window.innerWidth - gutter * 2) / 2;
	const viewportLeft = pageLeft - window.scrollX;
	const clamped = Math.min(
		Math.max(viewportLeft, half + gutter),
		window.innerWidth - half - gutter
	);
	return clamped + window.scrollX;
}
