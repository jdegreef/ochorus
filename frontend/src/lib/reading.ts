import { i18n } from './i18n.svelte';
import { getLang } from './lang.svelte';
import { MODERN_EDITION, baseEdition } from './reading-schema';
import { readingPace } from './readingPace.svelte';

/**
 * Estimated reading time in whole minutes from a word count, at THIS reader's
 * pace — measured from their own reading once there is enough of it, the
 * 200 wpm everyone was assumed to read at until then (see `readingPace`).
 * Reactive: a surface showing "12 min read" follows the pace as it settles.
 */
export function readingMinutes(words: number): number {
	return Math.max(1, Math.round(words / readingPace.wpm));
}

/**
 * Words a TTS voice speaks per minute at 1×. Natural speech is a good deal
 * slower than silent reading (~200 wpm), so a listen takes longer than a read.
 */
const LISTEN_WPM = 155;

/**
 * Estimated listen time in whole minutes, at speed multiplier `rate` (the
 * reader's chosen Listen speed, always a validated RATES member). Floored at 1
 * like `readingMinutes`.
 */
export function listenMinutes(words: number, rate = 1): number {
	return Math.max(1, Math.round(words / (LISTEN_WPM * rate)));
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
/**
 * A whole-minute count as a localized "N min / H hr / H hr M min" label, via a
 * locale key trio. Shared by readingTime and listenTime so the two format
 * identically. %n%/%h%/%m% (not {n}) so Paraglide doesn't treat these as params.
 */
function durationLabel(mins: number, keys: { min: string; hr: string; hrMin: string }): string {
	if (mins < 60) return i18n.t(keys.min).replace('%n%', String(mins));
	const h = Math.floor(mins / 60);
	const m = mins % 60;
	return m
		? i18n.t(keys.hrMin).replace('%h%', String(h)).replace('%m%', String(m))
		: i18n.t(keys.hr).replace('%h%', String(h));
}

export function readingTime(words: number): string {
	return durationLabel(readingMinutes(words), {
		min: 'common.minRead',
		hr: 'common.hrRead',
		hrMin: 'common.hrMinRead'
	});
}

/**
 * Localized "time left in the whole book" label, e.g. "3 hr 12 min left in
 * book" — the Kindle-style companion to the chapter's "N min left". Takes the
 * already-computed whole-minute count (via `readingMinutes`, at the reader's
 * pace) rather than words, so the caller can format from a memoized integer and
 * the message lookups don't re-run on every scroll pass. Same H/M formatter as
 * `readingTime`, so the two figures in the footer agree.
 */
export function bookTimeLeft(minutes: number): string {
	return durationLabel(minutes, {
		min: 'progress.bookMin',
		hr: 'progress.bookHr',
		hrMin: 'progress.bookHrMin'
	});
}

/**
 * Localized "time left in a reading plan", e.g. "4 hr 11 min left" — the plan
 * card's figure, so it reads in hours once a plan runs past the hour rather
 * than as "251 min left". Whole minutes in, like `bookTimeLeft`.
 */
export function planTimeLeft(minutes: number): string {
	return durationLabel(minutes, {
		min: 'plans.minLeft',
		hr: 'plans.hrLeft',
		hrMin: 'plans.hrMinLeft'
	});
}

/**
 * Localized listen-time label, e.g. "12 min listen" — the audio counterpart of
 * `readingTime`, at the reader's chosen `rate`. Same %n%/%h%/%m% templating so
 * word order stays correct per language.
 */
export function listenTime(words: number, rate = 1): string {
	return durationLabel(listenMinutes(words, rate), {
		min: 'common.minListen',
		hr: 'common.hrListen',
		hrMin: 'common.hrMinListen'
	});
}

/**
 * What a chapter is CALLED: its title, or "Chapter 3" when it has none.
 *
 * A chapter may genuinely have no title — Bounds's *Purpose in Prayer* is
 * thirteen untitled chapters, unnamed in the source — and every surface that
 * prints a chapter's name needs the same answer, or the reader gets a blank
 * heading, a `<title>` starting with an em-dash, and JSON-LD with `name: ""`.
 */
export function chapterName(order: number, title: string | null | undefined): string {
	return title || `${i18n.t('settings.chapterN')} ${order}`;
}

/**
 * How a chapter is named in a LIST: "3. The Letter Killeth".
 *
 * When there is no title the number is already inside the name, so it must not
 * also be prefixed — that is the "1. Chapter 1" this exists to avoid. Shared
 * because four places list chapters (the TOC, its bookmarks, the search drawer
 * and the notebook) and three had grown the same inline ternary.
 */
export function chapterLabel(order: number, title: string | null | undefined): string {
	return title ? `${order}. ${title}` : chapterName(order, title);
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
 * Does the reader want motion kept to a minimum? A tiny shared wrapper over the
 * media query, so the several places that pick `behavior: 'auto' | 'smooth'` for
 * a scroll ask it the same way. Call it from client code (event handlers,
 * effects) — `window` is assumed present.
 */
export function prefersReducedMotion(): boolean {
	return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}

/**
 * Run `place` once the prose has stopped moving, then once more after the next
 * frame — for restoring a reader to their paragraph.
 *
 * `await tick()` is not enough, and the gap is not small. It waits for Svelte to
 * write the DOM, not for the browser to finish laying it out: measured on a
 * chapter restore, the document grew from 6,010px to 6,673px between the scroll
 * and the following frame, carrying the target paragraph 209px down with it.
 * Webfonts are the bulk of it — this is a reading app, and its prose faces load
 * after first paint.
 *
 * That mattered because the resume point WALKED BACKWARDS. The scroll landed
 * the paragraph 35px lower than intended, which left the paragraph above it
 * still crossing the header line, so the next save recorded N-1 — and every
 * reopen lost another one: a chapter opened at paragraph 8 read 7, then 6, then
 * 5, and eventually the top.
 *
 * Both passes are needed, and neither is a guess: the first puts the reader
 * roughly right immediately rather than leaving them at the top while fonts
 * load, and the second corrects for the reflow once it has happened.
 */
export function placeAfterLayout(place: () => void): void {
	place();
	const again = () => requestAnimationFrame(place);
	// `fonts.ready` has usually resolved by the time a client-side navigation
	// runs, in which case this is just the extra frame.
	if (typeof document !== 'undefined' && document.fonts) void document.fonts.ready.then(again);
	else again();
}

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
	return baseEdition(language);
}

/**
 * The content language a reader on `edition` is actually reading — what to
 * fetch, and what any annotation of that text belongs to.
 *
 * One helper because the mapping was written out at three call sites (the
 * chapter fetch, the TOC drawer, the reader's marks), and a highlight landing
 * on the wrong edition is precisely what happens when two of them agree and
 * the third doesn't.
 */
export function editionLang(edition: 'modern' | null): string {
	return edition === 'modern' ? MODERN_EDITION : getLang();
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
