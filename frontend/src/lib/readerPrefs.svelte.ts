import { browser } from '$app/environment';

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

export const LEADING: Record<Leading, number> = {
	compact: 1.55,
	normal: 1.85,
	relaxed: 2.2
};

export const MEASURE: Record<Measure, string> = {
	narrow: '34rem',
	normal: '42rem',
	wide: '52rem'
};

export const FONT_STACK: Record<ReaderFont, string> = {
	serif: "'Fraunces Variable', Georgia, 'Times New Roman', serif",
	sans: "'Hanken Grotesk Variable', ui-sans-serif, system-ui, sans-serif",
	dyslexic: "'OpenDyslexic', 'Comic Sans MS', cursive"
};

const SCALE_MIN = 0.8;
const SCALE_MAX = 1.6;

const KEY = 'ochorus:reader-prefs';

interface Stored {
	scale: number;
	leading: Leading;
	measure: Measure;
	font: ReaderFont;
	paged: boolean;
}

const DEFAULTS: Stored = {
	scale: 1,
	leading: 'normal',
	measure: 'normal',
	font: 'serif',
	paged: false
};

function load(): Stored {
	if (!browser) return { ...DEFAULTS };
	try {
		const raw = JSON.parse(localStorage.getItem(KEY) || '{}');
		const scale = Number.isFinite(raw.scale)
			? Math.min(SCALE_MAX, Math.max(SCALE_MIN, raw.scale))
			: DEFAULTS.scale;
		return {
			scale,
			leading: raw.leading in LEADING ? raw.leading : DEFAULTS.leading,
			measure: raw.measure in MEASURE ? raw.measure : DEFAULTS.measure,
			font: raw.font in FONT_STACK ? raw.font : DEFAULTS.font,
			paged: typeof raw.paged === 'boolean' ? raw.paged : DEFAULTS.paged
		};
	} catch {
		return { ...DEFAULTS };
	}
}

class ReaderPrefs {
	scale = $state(DEFAULTS.scale);
	leading = $state<Leading>(DEFAULTS.leading);
	measure = $state<Measure>(DEFAULTS.measure);
	font = $state<ReaderFont>(DEFAULTS.font);
	paged = $state(DEFAULTS.paged);
	#loaded = false;

	/** Hydrate from localStorage. Safe to call repeatedly (runs once). */
	init() {
		if (this.#loaded || !browser) return;
		const s = load();
		this.scale = s.scale;
		this.leading = s.leading;
		this.measure = s.measure;
		this.font = s.font;
		this.paged = s.paged;
		this.#loaded = true;
	}

	#save() {
		if (!browser) return;
		const s: Stored = {
			scale: this.scale,
			leading: this.leading,
			measure: this.measure,
			font: this.font,
			paged: this.paged
		};
		localStorage.setItem(KEY, JSON.stringify(s));
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
	setPaged(v: boolean) {
		this.paged = v;
		this.#save();
	}

	/** Inline `style` string for the reading <article>. */
	get style(): string {
		return [
			`--reading-scale:${this.scale}`,
			`--reading-leading:${LEADING[this.leading]}`,
			`--reading-measure:${MEASURE[this.measure]}`,
			`--reading-font:${FONT_STACK[this.font]}`
		].join(';');
	}
}

export const readerPrefs = new ReaderPrefs();
