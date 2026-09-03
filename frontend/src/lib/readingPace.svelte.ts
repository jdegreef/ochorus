import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import { PACE_KEY } from './reading-schema';

/**
 * The reader's own pace, for every "N min read" and "M min left" in the app.
 *
 * Until now those all assumed 200 words a minute — right for nobody in
 * particular, and a long way off for a slow careful reader, a fast one, or
 * anyone reading in a second language. This keeps a running tally of words
 * read over milliseconds spent (fed by the chapter reader from its own
 * paragraph samples — see `pace.ts`, which owns the plausibility rules) and
 * answers with the measured rate once there is enough of it to trust. Before
 * that, the old constant.
 *
 * Device-local on purpose: a pace is a property of the reader-on-this-device
 * (a phone in a queue and a desk at home read differently), and it is only an
 * estimate, so it is not worth a sync round-trip. It IS in READING_DATA_KEYS,
 * though: on a shared device the next reader must not inherit it, and
 * "clear reading data" must be able to reset it.
 */

/** What every estimate assumed before, and still does until there is data. */
export const DEFAULT_WPM = 200;
/** Words read before the measured rate is trusted (~7 min at the default). */
export const TRUST_WORDS = 1500;
/** Sanity bounds on the answer, whatever the tally says. */
export const WPM_MIN = 80;
export const WPM_MAX = 700;
/** Past this many words the tally is halved, so recent reading weighs most. */
const DECAY_WORDS = 30_000;

export interface Stored {
	words: number;
	ms: number;
}

const DEFAULTS: Stored = { words: 0, ms: 0 };

const finiteNonNegative = (v: unknown): v is number =>
	typeof v === 'number' && Number.isFinite(v) && v >= 0;

/** Exported for tests: the store hydrates with it at load and on `ochorus:sync`. */
export function load(): Stored {
	const raw = readJSON<Record<string, unknown>>(PACE_KEY, {});
	return {
		words: finiteNonNegative(raw.words) ? raw.words : DEFAULTS.words,
		ms: finiteNonNegative(raw.ms) ? raw.ms : DEFAULTS.ms
	};
}

/** The rate a tally answers with: measured once trusted, else the default. */
export function effectiveWpm(s: Stored): number {
	if (s.words < TRUST_WORDS || s.ms <= 0) return DEFAULT_WPM;
	const wpm = Math.round((s.words / s.ms) * 60_000);
	return Math.min(WPM_MAX, Math.max(WPM_MIN, wpm));
}

class ReadingPace {
	words = $state(DEFAULTS.words);
	ms = $state(DEFAULTS.ms);

	/** Words per minute to estimate with. Derived, so the many surfaces that
	 *  show a reading time re-render only when the rounded rate actually
	 *  changes — not on every sample that nudges the tally. */
	wpm = $derived(effectiveWpm({ words: this.words, ms: this.ms }));

	/** True once estimates are the reader's own rather than the default. */
	personalized = $derived(this.words >= TRUST_WORDS && this.ms > 0);

	// Hydrated at module load rather than lazily on first read: the readers are
	// template expressions (`readingTime(...)` in a card), and Svelte forbids a
	// state write from inside one — a lazy `init()` there is exactly that.
	// Prerendered HTML carries the default; the client re-renders at the
	// measured pace on hydration.
	constructor() {
		if (!browser) return;
		this.#hydrate();
		// Another tab's samples, or a wipe (sign-out, "clear reading data"),
		// replaced the cache underneath us: re-read, like every other store.
		window.addEventListener('ochorus:sync', () => this.#hydrate());
	}

	#hydrate() {
		const s = load();
		this.words = s.words;
		this.ms = s.ms;
	}

	/**
	 * Add a stretch of reading: `words` read over `ms`. Callers are trusted to
	 * have applied `pace.ts`'s plausibility rules; the store only refuses the
	 * degenerate (nothing read, no time passed).
	 */
	record(words: number, ms: number) {
		if (!(words > 0) || !(ms > 0)) return;
		// Re-read first so two tabs sampling at once add to, not overwrite,
		// each other's tally.
		const s = load();
		let w = s.words + words;
		let m = s.ms + ms;
		if (w > DECAY_WORDS) {
			w /= 2;
			m /= 2;
		}
		this.words = w;
		this.ms = m;
		writeJSON(PACE_KEY, { words: w, ms: m } satisfies Stored);
	}

	reset() {
		this.words = DEFAULTS.words;
		this.ms = DEFAULTS.ms;
		writeJSON(PACE_KEY, DEFAULTS);
	}
}

export const readingPace = new ReadingPace();
