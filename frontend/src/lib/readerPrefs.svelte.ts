import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';

/**
 * Reader comfort preferences — font size, leading (line-height), measure (column
 * width) and typeface. Device-local in localStorage and shared across every
 * chapter. When login lands these sync to the user's profile (see auth store),
 * but localStorage stays as the instant-load cache.
 *
 * Each preference maps to a CSS custom property set on the reading <article>;
 * `.reading` in app.css consumes them.
 */

export type Leading = 'compact' | 'normal' | 'relaxed';
export type Measure = 'narrow' | 'normal' | 'wide' | 'xwide';
export type ReaderFont = 'serif' | 'sans' | 'dyslexic';
export type Align = 'left' | 'justify';
export type Margin = 'narrow' | 'normal' | 'generous';

export const LEADING: Record<Leading, number> = {
	compact: 1.55,
	normal: 1.85,
	relaxed: 2.2
};

/**
 * Column width, as a multiple of the reader's own text size.
 *
 * These were plain `rem`, i.e. independent of `--reading-scale` — so "normal"
 * held ~75 characters per line at 1x but only ~47 at the maximum 1.6x. The
 * comfortable 65-75 band held at exactly one setting, and the readers most
 * likely to enlarge the text got the most cramped, most ragged column.
 *
 * Scaling the width with the text keeps the character count roughly constant
 * instead. The measure is applied to the <article>, whose own font-size is the
 * root's, so this cannot be expressed in `em` — hence the explicit calc.
 */
const MEASURE_REM: Record<Measure, number> = {
	narrow: 34,
	normal: 42,
	wide: 52,
	// For big displays: 52rem "wide" still reads as a ribbon on a 27" screen.
	xwide: 64
};

export const MEASURE: Record<Measure, string> = {
	narrow: `calc(${MEASURE_REM.narrow}rem * var(--reading-scale, 1))`,
	normal: `calc(${MEASURE_REM.normal}rem * var(--reading-scale, 1))`,
	wide: `calc(${MEASURE_REM.wide}rem * var(--reading-scale, 1))`,
	xwide: `calc(${MEASURE_REM.xwide}rem * var(--reading-scale, 1))`
};

/**
 * Side gutters of the reading column in scroll mode — the space between the
 * text and the screen edge on a phone or tablet, where the column runs edge
 * to edge and this is the knob that pulls it in. Page mode keeps its own tuned
 * gutters (`--pgpad`) and is unaffected.
 *
 * Honest caveat for wide viewports: the gutter is padding INSIDE the article's
 * measure-capped box (border-box), so once the screen is wider than the
 * column — desktop, where the auto margins already supply the whitespace —
 * "Generous" trims the text column rather than adding space around it. That is
 * how the fixed 1.25rem gutter always behaved; the setting just makes the
 * amount a choice. It does what the label says on the devices it's for.
 */
export const MARGIN: Record<Margin, string> = {
	narrow: '0.75rem',
	normal: '1.25rem',
	generous: '2.5rem'
};

// A tablet in portrait (or a small landscape one): wide enough that the normal
// 42rem column leaves the page looking like a phone column floating in
// whitespace, but below the 1024px at which the reader goes two-column paged.
const TABLET_MIN = 768;
const TABLET_MAX = 1024;

/**
 * The first-run column width for a viewport. Tablets default to `wide` so the
 * text fills the page; phones and desktops keep `normal` (desktops get the
 * two-column spread instead). Only the DEFAULT — a measure the reader has
 * chosen is stored and honoured everywhere. Pure, so it's unit-testable.
 */
export function defaultMeasureFor(innerWidth: number): Measure {
	return innerWidth >= TABLET_MIN && innerWidth < TABLET_MAX ? 'wide' : 'normal';
}

// NOTE: browse-page width is no longer derived from the reading measure. The
// page shell is driven by the independent `pageWidth` store (see
// $lib/pageWidth.svelte) and the shared `.page-col` class; MEASURE below stays
// purely the prose column inside a chapter.

/**
 * The three faces a reader can choose, as CSS `font-family` values.
 *
 * TWO OF THESE NAME A TOKEN RATHER THAN A STACK, and that is the point. They
 * used to spell Fraunces and Hanken out here, which made this a third copy of
 * a list `app.css` already declares twice — and copies drift silently, because
 * nothing renders both. The reader is the app's most-read surface, so the copy
 * that drifted was the one that mattered: `--font-display` grew Arabic,
 * Devanagari and Cyrillic faces and the READER did not, since
 * `--reading-font` is always set from here and the `var(--reading-font,
 * var(--font-display))` fallback in `.reading` therefore never fires.
 *
 * A `var()` is legal here: these land in a custom property on the reading
 * article, and substitution is token-level, so `--reading-font:var(--font-display)`
 * resolves exactly as the literal stack would.
 *
 * DYSLEXIC NAMES ONE LITERAL AND THEN THE TOKEN, because only OpenDyslexic
 * itself has no token — the tail does. It is the one preference this change
 * cannot honour outside Latin: OpenDyslexic is Latin-only and no Arabic or
 * Devanagari equivalent exists, so an Arabic reader who asked for it was
 * getting `cursive`, a generic that matches every glyph and hands the script to
 * whatever the device felt like. Ending at `var(--font-display)` puts that
 * reader on Amiri or Tiro instead — the same text they would get without the
 * preference rather than something worse — and, unlike spelling those three
 * families out here, it cannot drift from the stack they are named in. What the
 * setting SHOULD do for those readers is a product question, not a CSS one.
 */
export const FONT_STACK: Record<ReaderFont, string> = {
	serif: 'var(--font-display)',
	sans: 'var(--font-sans)',
	dyslexic: "'OpenDyslexic', 'Comic Sans MS', var(--font-display)"
};

const SCALE_MIN = 0.8;
const SCALE_MAX = 1.6;

// Viewport width (px) at/above which the page-turn layout is the first-run
// default — wide enough for a comfortable two-column spread. Matches the
// reader's own two-column threshold.
const WIDE_SCREEN_MIN = 1024;

const KEY = 'ochorus:reader-prefs';

interface Stored {
	scale: number;
	leading: Leading;
	measure: Measure;
	font: ReaderFont;
	align: Align;
	margin: Margin;
	paged: boolean;
	tapToScroll: boolean;
	preferModern: boolean;
}

const DEFAULTS: Stored = {
	scale: 1,
	leading: 'normal',
	measure: 'normal',
	font: 'serif',
	align: 'left',
	margin: 'normal',
	paged: false,
	// Off by default: tapping the body to scroll is opt-in. An implicit version
	// of the sibling idea (edge-tap to change chapter) was a footgun on phones
	// and was removed; this one only turns on when a reader asks for it.
	tapToScroll: false,
	preferModern: false
};

const ALIGNS: readonly Align[] = ['left', 'justify'];

/** Exported for tests: the store's own `init()` runs it once per page load. */
export function load(): Stored {
	const raw = readJSON<Record<string, unknown>>(KEY, {});
	const scale =
		typeof raw.scale === 'number' && Number.isFinite(raw.scale)
			? Math.min(SCALE_MAX, Math.max(SCALE_MIN, raw.scale))
			: DEFAULTS.scale;
	return {
		scale,
		leading: (raw.leading as Leading) in LEADING ? (raw.leading as Leading) : DEFAULTS.leading,
		// A stored measure always wins; only a first run picks by device class.
		measure:
			(raw.measure as Measure) in MEASURE
				? (raw.measure as Measure)
				: browser
					? defaultMeasureFor(window.innerWidth)
					: DEFAULTS.measure,
		font: (raw.font as ReaderFont) in FONT_STACK ? (raw.font as ReaderFont) : DEFAULTS.font,
		align: ALIGNS.includes(raw.align as Align) ? (raw.align as Align) : DEFAULTS.align,
		// hasOwn, not `in`: `in` walks the prototype, so a stored "constructor"
		// would pass and inject `function Object()` into the article's style.
		margin: Object.hasOwn(MARGIN, String(raw.margin)) ? (raw.margin as Margin) : DEFAULTS.margin,
		// Default to the page-turn (two-column) layout on wide screens, where it
		// reads like an open book; keep scrolling on phones/tablets. Once the
		// reader picks a layout it's stored and honoured everywhere.
		paged:
			typeof raw.paged === 'boolean'
				? raw.paged
				: browser && window.innerWidth >= WIDE_SCREEN_MIN,
		tapToScroll:
			typeof raw.tapToScroll === 'boolean' ? raw.tapToScroll : DEFAULTS.tapToScroll,
		preferModern: typeof raw.preferModern === 'boolean' ? raw.preferModern : DEFAULTS.preferModern
	};
}

class ReaderPrefs {
	scale = $state(DEFAULTS.scale);
	leading = $state<Leading>(DEFAULTS.leading);
	measure = $state<Measure>(DEFAULTS.measure);
	font = $state<ReaderFont>(DEFAULTS.font);
	align = $state<Align>(DEFAULTS.align);
	/** Side gutters of the reading column in scroll mode. */
	margin = $state<Margin>(DEFAULTS.margin);
	paged = $state(DEFAULTS.paged);
	/** Opt-in: in scroll mode, a tap in the lower part of the screen pages down. */
	tapToScroll = $state(DEFAULTS.tapToScroll);
	/** When a Modern English edition exists, open it by default (device-local). */
	preferModern = $state(DEFAULTS.preferModern);
	#loaded = false;

	/** Hydrate from localStorage. Safe to call repeatedly (runs once). */
	init() {
		if (this.#loaded || !browser) return;
		const s = load();
		this.scale = s.scale;
		this.leading = s.leading;
		this.measure = s.measure;
		this.font = s.font;
		this.align = s.align;
		this.margin = s.margin;
		this.paged = s.paged;
		this.tapToScroll = s.tapToScroll;
		this.preferModern = s.preferModern;
		this.#loaded = true;
	}

	#save() {
		const s: Stored = {
			scale: this.scale,
			leading: this.leading,
			measure: this.measure,
			font: this.font,
			align: this.align,
			margin: this.margin,
			paged: this.paged,
			tapToScroll: this.tapToScroll,
			preferModern: this.preferModern
		};
		writeJSON(KEY, s);
	}

	setScale(next: number) {
		this.scale = Math.min(SCALE_MAX, Math.max(SCALE_MIN, Math.round(next * 20) / 20));
		this.#save();
	}
	bumpScale(delta: number) {
		this.setScale(this.scale + delta);
	}
	setLeading(v: Leading) {
		this.leading = v;
		this.#save();
	}
	setMeasure(v: Measure) {
		this.measure = v;
		this.#save();
	}
	setFont(v: ReaderFont) {
		this.font = v;
		this.#save();
	}
	setAlign(v: Align) {
		this.align = v;
		this.#save();
	}
	setMargin(v: Margin) {
		this.margin = v;
		this.#save();
	}
	setPaged(v: boolean) {
		this.paged = v;
		this.#save();
	}
	setTapToScroll(v: boolean) {
		this.tapToScroll = v;
		this.#save();
	}
	setPreferModern(v: boolean) {
		this.preferModern = v;
		this.#save();
	}

	/** Restore every reader comfort preference to its default (Settings → reset).
	 *  Does not touch reading data (progress, highlights) — only preferences. */
	reset() {
		this.scale = DEFAULTS.scale;
		this.leading = DEFAULTS.leading;
		// Back to the first-run default for THIS device, not the bare constant —
		// otherwise a tablet reader who resets can never regain the wide column
		// its first run gave it (reset() saves, so the no-pref branch never fires).
		this.measure = browser ? defaultMeasureFor(window.innerWidth) : DEFAULTS.measure;
		this.font = DEFAULTS.font;
		this.align = DEFAULTS.align;
		this.margin = DEFAULTS.margin;
		this.paged = DEFAULTS.paged;
		this.tapToScroll = DEFAULTS.tapToScroll;
		this.preferModern = DEFAULTS.preferModern;
		this.#save();
	}

	/** Inline `style` string for the reading <article>. */
	get style(): string {
		return [
			`--reading-scale:${this.scale}`,
			`--reading-leading:${LEADING[this.leading]}`,
			`--reading-measure:${MEASURE[this.measure]}`,
			`--reading-font:${FONT_STACK[this.font]}`,
			`--reading-align:${this.align === 'justify' ? 'justify' : 'start'}`,
			`--reading-margin:${MARGIN[this.margin]}`,
			`--reading-hyphens:${this.align === 'justify' ? 'auto' : 'manual'}`
		].join(';');
	}
}

export const readerPrefs = new ReaderPrefs();
