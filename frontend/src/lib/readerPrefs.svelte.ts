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
export type ReaderFont =
	| 'serif'
	| 'sans'
	| 'literata'
	| 'garamond'
	| 'sourceSerif'
	| 'lora'
	| 'baskerville'
	| 'merriweather'
	| 'hyperlegible'
	| 'dyslexic';
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
 * The faces a reader can choose, as CSS `font-family` values, in picker order.
 *
 * Each names at most one family and then a HOUSE token, never a spelled-out
 * stack and never --font-display / --font-sans: the tail is where the Arabic,
 * Devanagari and Cyrillic faces live, and the house tokens are the ones a site
 * style cannot move (site-fonts.css explains the mechanism). A `var()` is legal
 * here because these land in a custom property on the reading article.
 * `fontStacks.test.ts` gates every entry for script coverage and imports.
 */
export const FONT_STACK: Record<ReaderFont, string> = {
	serif: 'var(--house-display)',
	sans: 'var(--house-sans)',
	literata: "'Literata Variable', var(--house-display)",
	garamond: "'EB Garamond Variable', var(--house-display)",
	sourceSerif: "'Source Serif 4 Variable', var(--house-display)",
	lora: "'Lora Variable', var(--house-display)",
	baskerville: "'Libre Baskerville', var(--house-display)",
	merriweather: "'Merriweather Variable', var(--house-display)",
	hyperlegible: "'Atkinson Hyperlegible Next Variable', var(--house-sans)",
	dyslexic: "'OpenDyslexic', 'Comic Sans MS', var(--house-display)"
};

/** The faces that describe a kind rather than name a family; each picker
 *  translates these in its own words. */
export type FontKind = 'serif' | 'sans' | 'dyslexic';

/** Display names of the named faces. Proper nouns, so not in the message
 *  catalogues — a typeface is called Lora in every language. */
const FONT_NAME: Record<Exclude<ReaderFont, FontKind>, string> = {
	literata: 'Literata',
	garamond: 'EB Garamond',
	sourceSerif: 'Source Serif',
	lora: 'Lora',
	baskerville: 'Baskerville',
	merriweather: 'Merriweather',
	hyperlegible: 'Atkinson Hyperlegible'
};

/** A picker label: the face's own name, or the caller's word for its kind. */
export function fontLabel(v: ReaderFont, kinds: Record<FontKind, string>): string {
	return Object.hasOwn(FONT_NAME, v) ? FONT_NAME[v as keyof typeof FONT_NAME] : kinds[v as FontKind];
}

/** Every reader face, in picker order. */
export const READER_FONTS = Object.keys(FONT_STACK) as ReaderFont[];

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
	// Whether the reader has explicitly picked an alignment. Until they do, the
	// effective alignment is chosen per layout — paged reads justified (like a
	// printed page / Kindle), scroll stays left-ragged — see `effectiveAlign`.
	alignChosen: boolean;
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
	alignChosen: false,
	margin: 'normal',
	paged: false,
	// Off by default: tapping the body to scroll is opt-in. An implicit version
	// of the sibling idea (edge-tap to change chapter) was a footgun on phones
	// and was removed; this one only turns on when a reader asks for it.
	tapToScroll: false,
	preferModern: false
};

const ALIGNS: readonly Align[] = ['left', 'justify'];

/** The CSS value for a reader alignment: justify → `justify`, left → `start`
 *  (logical, so it flips correctly in RTL). One owner for the mapping, shared by
 *  the article style pipeline and the settings-panel preview. */
export function cssAlign(a: Align): 'justify' | 'start' {
	return a === 'justify' ? 'justify' : 'start';
}

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
		// hasOwn for the reason `margin` gives below. A face this build no longer
		// ships lands on the default rather than on an unset --reading-font.
		font: Object.hasOwn(FONT_STACK, String(raw.font)) ? (raw.font as ReaderFont) : DEFAULTS.font,
		align: ALIGNS.includes(raw.align as Align) ? (raw.align as Align) : DEFAULTS.align,
		alignChosen:
			typeof raw.alignChosen === 'boolean' ? raw.alignChosen : DEFAULTS.alignChosen,
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
	/** True once the reader picks an alignment; until then it's layout-derived. */
	alignChosen = $state(DEFAULTS.alignChosen);
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
		this.alignChosen = s.alignChosen;
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
			alignChosen: this.alignChosen,
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
		this.alignChosen = true;
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
		this.alignChosen = DEFAULTS.alignChosen;
		this.margin = DEFAULTS.margin;
		this.paged = DEFAULTS.paged;
		this.tapToScroll = DEFAULTS.tapToScroll;
		this.preferModern = DEFAULTS.preferModern;
		this.#save();
	}

	/**
	 * The alignment actually in force for a given layout. An explicit choice wins
	 * everywhere; until the reader makes one, paged mode reads justified (a
	 * printed-page / Kindle look) while scroll stays left-ragged. `get style()`
	 * already emits the scroll answer (it equals this for paged === false), so the
	 * page reader only overrides the paged, still-unchosen case.
	 */
	effectiveAlign(paged: boolean): Align {
		return this.alignChosen ? this.align : paged ? 'justify' : 'left';
	}

	/**
	 * Inline `style` string for the reading <article>, with alignment resolved for
	 * a given layout — the one place align/hyphens become CSS. `paged` reads
	 * justified (a printed-page look) until the reader chooses; scroll stays
	 * left-ragged. The paged chapter reader calls `styleFor(true)`; everything
	 * else uses `style` (= `styleFor(false)`), whose output is unchanged.
	 */
	styleFor(paged = false): string {
		const align = this.effectiveAlign(paged);
		return [
			`--reading-scale:${this.scale}`,
			`--reading-leading:${LEADING[this.leading]}`,
			`--reading-measure:${MEASURE[this.measure]}`,
			`--reading-font:${FONT_STACK[this.font]}`,
			`--reading-align:${cssAlign(align)}`,
			`--reading-margin:${MARGIN[this.margin]}`,
			`--reading-hyphens:${align === 'justify' ? 'auto' : 'manual'}`
		].join(';');
	}

	/** Inline `style` string for a scroll reading surface (the common case). */
	get style(): string {
		return this.styleFor(false);
	}
}

export const readerPrefs = new ReaderPrefs();
