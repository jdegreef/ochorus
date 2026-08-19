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
export type Measure = 'narrow' | 'normal' | 'wide';
export type ReaderFont = 'serif' | 'sans' | 'dyslexic';
export type Align = 'left' | 'justify';

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
	wide: 52
};

export const MEASURE: Record<Measure, string> = {
	narrow: `calc(${MEASURE_REM.narrow}rem * var(--reading-scale, 1))`,
	normal: `calc(${MEASURE_REM.normal}rem * var(--reading-scale, 1))`,
	wide: `calc(${MEASURE_REM.wide}rem * var(--reading-scale, 1))`
};

// NOTE: browse-page width is no longer derived from the reading measure. The
// page shell is driven by the independent `pageWidth` store (see
// $lib/pageWidth.svelte) and the shared `.page-col` class; MEASURE below stays
// purely the prose column inside a chapter.

export const FONT_STACK: Record<ReaderFont, string> = {
	serif: "'Fraunces Variable', Georgia, 'Times New Roman', serif",
	sans: "'Hanken Grotesk Variable', ui-sans-serif, system-ui, sans-serif",
	dyslexic: "'OpenDyslexic', 'Comic Sans MS', cursive"
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
	paged: boolean;
	preferModern: boolean;
}

const DEFAULTS: Stored = {
	scale: 1,
	leading: 'normal',
	measure: 'normal',
	font: 'serif',
	align: 'left',
	paged: false,
	preferModern: false
};

const ALIGNS: readonly Align[] = ['left', 'justify'];

function load(): Stored {
	const raw = readJSON<Record<string, unknown>>(KEY, {});
	const scale =
		typeof raw.scale === 'number' && Number.isFinite(raw.scale)
			? Math.min(SCALE_MAX, Math.max(SCALE_MIN, raw.scale))
			: DEFAULTS.scale;
	return {
		scale,
		leading: (raw.leading as Leading) in LEADING ? (raw.leading as Leading) : DEFAULTS.leading,
		measure: (raw.measure as Measure) in MEASURE ? (raw.measure as Measure) : DEFAULTS.measure,
		font: (raw.font as ReaderFont) in FONT_STACK ? (raw.font as ReaderFont) : DEFAULTS.font,
		align: ALIGNS.includes(raw.align as Align) ? (raw.align as Align) : DEFAULTS.align,
		// Default to the page-turn (two-column) layout on wide screens, where it
		// reads like an open book; keep scrolling on phones/tablets. Once the
		// reader picks a layout it's stored and honoured everywhere.
		paged:
			typeof raw.paged === 'boolean'
				? raw.paged
				: browser && window.innerWidth >= WIDE_SCREEN_MIN,
		preferModern: typeof raw.preferModern === 'boolean' ? raw.preferModern : DEFAULTS.preferModern
	};
}

class ReaderPrefs {
	scale = $state(DEFAULTS.scale);
	leading = $state<Leading>(DEFAULTS.leading);
	measure = $state<Measure>(DEFAULTS.measure);
	font = $state<ReaderFont>(DEFAULTS.font);
	align = $state<Align>(DEFAULTS.align);
	paged = $state(DEFAULTS.paged);
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
		this.paged = s.paged;
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
			paged: this.paged,
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
	setPaged(v: boolean) {
		this.paged = v;
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
		this.measure = DEFAULTS.measure;
		this.font = DEFAULTS.font;
		this.align = DEFAULTS.align;
		this.paged = DEFAULTS.paged;
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
			`--reading-hyphens:${this.align === 'justify' ? 'auto' : 'manual'}`
		].join(';');
	}
}

export const readerPrefs = new ReaderPrefs();
