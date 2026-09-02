import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';

/**
 * "Listen" mode — reads the open chapter aloud with the browser's built-in
 * SpeechSynthesis voices. No audio files, no network: it works offline and in
 * every language the device has a voice for.
 *
 * The chapter is spoken one paragraph per utterance rather than as one long
 * text: that gives exact paragraph boundaries for highlight-as-you-listen,
 * lets rate/voice changes apply immediately (restart the current paragraph,
 * not the chapter), and sidesteps Chrome's notorious stall on long utterances.
 *
 * Rate and voice are device preferences, persisted in localStorage.
 */

/** Notable speeds for the Listen bar's quick-cycle button. Settings offers the
 *  full continuous range between RATE_MIN and RATE_MAX. */
export const RATES = [0.8, 1, 1.25, 1.5, 1.75, 2] as const;
export const RATE_MIN = 0.5;
export const RATE_MAX = 2;

/** A requested speed snapped into range and onto a clean 0.05 step. */
export function clampRate(rate: number): number {
	return Math.min(RATE_MAX, Math.max(RATE_MIN, Math.round(rate * 20) / 20));
}

const KEY = 'ochorus:listen';

/**
 * The voice to reach for, per language, when the listener hasn't chosen one —
 * matched by name substring. English defaults to Google UK English Male
 * (Chrome's warm British male voice); where it isn't installed (Safari, iOS,
 * Firefox) we fall back to the top-ranked device voice.
 */
const PREFERRED_DEFAULTS: Record<string, RegExp> = {
	en: /google uk english male/i
};

interface Stored {
	rate: number;
	voiceURI: string;
}

export interface StartOptions {
	/** Content language (BCP-47); decides the voice and utterance lang. */
	lang?: string;
	/** OS Media Session metadata (lock-screen / background controls). */
	media?: { title: string; artist?: string };
	/** Fires when playback runs off the end on its own — audiobook roll-over. */
	onFinish?: () => void;
	/** Fires as each paragraph `index` begins, driven by the audio (not a
	 *  reactive effect) — the reader saves the resume point from it. */
	onAdvance?: (index: number) => void;
}

function loadPrefs(): Stored {
	const raw = readJSON<{ rate?: number; voiceURI?: unknown }>(KEY, {});
	return {
		// Any speed inside the range — Settings is a continuous slider now, so a
		// saved value need not be one of the RATES presets.
		rate:
			typeof raw.rate === 'number' && raw.rate >= RATE_MIN && raw.rate <= RATE_MAX
				? raw.rate
				: 1,
		voiceURI: typeof raw.voiceURI === 'string' ? raw.voiceURI : ''
	};
}

class Listen {
	readonly supported = browser && 'speechSynthesis' in window;

	status = $state<'idle' | 'playing' | 'paused'>('idle');
	/** Index of the paragraph being spoken; -1 when idle. */
	current = $state(-1);
	total = $state(0);
	rate = $state(1);
	voiceURI = $state('');
	voices = $state<SpeechSynthesisVoice[]>([]);
	/** Minutes until playback auto-stops (0 = off). Session-only, not persisted. */
	sleepMinutes = $state(0);
	/**
	 * True when a `start()` was asked for but no voice the reader would actually
	 * speak with resolves — reading would be silent, so the reader shows a
	 * one-line explanation instead of a Listen bar that never makes a sound.
	 */
	noVoice = $state(false);

	#paragraphs: string[] = [];
	#lang = 'en';
	#media: { title: string; artist?: string } | null = null;
	// Called once when playback runs off the end of the paragraphs on its own —
	// NOT on a user stop or a navigation. The book reader uses it to roll into
	// the next chapter. Held per start() and cleared by stop().
	#onFinish: (() => void) | null = null;
	// Called as each paragraph begins (the audio drives it) — the reader saves
	// the resume point from it. Held per start() and cleared by stop().
	#onAdvance: ((index: number) => void) | null = null;
	#mediaBound = false;
	#sleepTimer: ReturnType<typeof setTimeout> | null = null;
	// Keep a reference to the active utterance — Chrome garbage-collects it
	// otherwise and the onend callback (our advance mechanism) never fires.
	#utterance: SpeechSynthesisUtterance | null = null;
	#initialized = false;

	init() {
		if (!this.supported || this.#initialized) return;
		this.#initialized = true;
		const prefs = loadPrefs();
		this.rate = prefs.rate;
		this.voiceURI = prefs.voiceURI;

		const load = () => (this.voices = speechSynthesis.getVoices());
		load();
		speechSynthesis.addEventListener?.('voiceschanged', load);
	}

	/**
	 * The best voices for a language (BCP-47 prefix), capped — for the Settings
	 * voice picker. The browser's raw list is long, device-dependent, and full of
	 * robotic legacy voices; this surfaces only the top few. "Best" heuristic:
	 * prefer natural/neural cloud voices (Google, Neural, Premium, Enhanced,
	 * WaveNet, Siri) and known-good system voices, then the platform default, then
	 * cloud over local — deduped by name so a voice listed twice appears once. A
	 * language's preferred default (`PREFERRED_DEFAULTS`) outranks everything, so
	 * it leads the picker and is what `defaultVoice` returns.
	 */
	topVoices(langCode: string, max = 4): SpeechSynthesisVoice[] {
		const matches = this.#voicesForLang(langCode);
		const preferred = PREFERRED_DEFAULTS[this.#langPrefix(langCode)];
		const NATURAL = /google|neural|natural|premium|enhanced|wavenet|siri/i;
		// Apple's higher-quality named voices (they don't advertise "natural").
		const NAMED = /samantha|daniel|karen|moira|tessa|serena|allison|ava|zoe|nicky|aaron|fiona|rishi/i;
		const score = (v: SpeechSynthesisVoice) =>
			(preferred?.test(v.name) ? 10 : 0) +
			(NATURAL.test(v.name) ? 5 : 0) +
			(NAMED.test(v.name) ? 2 : 0) +
			(v.default ? 1 : 0) +
			(v.localService ? 0 : 1);
		const byName = new Map<string, SpeechSynthesisVoice>();
		for (const v of [...matches].sort((a, b) => score(b) - score(a))) {
			if (!byName.has(v.name)) byName.set(v.name, v);
		}
		return [...byName.values()].slice(0, max);
	}

	/**
	 * The voice to use for `lang` when the listener hasn't picked one: the
	 * language's preferred default (e.g. Google UK English Male for English) if
	 * the device has it, otherwise the top-ranked device voice. This is exactly
	 * the head of `topVoices`, so the picker's first option and the reading
	 * voice never disagree.
	 */
	defaultVoice(lang: string): SpeechSynthesisVoice | undefined {
		return this.topVoices(lang, 1)[0];
	}

	/**
	 * The voice to actually speak with: `preferURI` (the listener's saved choice
	 * by default) if it's still present on the device, otherwise the language
	 * default from `defaultVoice`.
	 */
	resolveVoice(lang = this.#lang, preferURI = this.voiceURI): SpeechSynthesisVoice | undefined {
		if (preferURI) {
			const chosen = this.voices.find((v) => v.voiceURI === preferURI);
			if (chosen) return chosen;
		}
		return this.defaultVoice(lang);
	}

	/** Clear the missing-voice notice (the listener dismissed it). */
	dismissNoVoice() {
		this.noVoice = false;
	}

	#langPrefix(lang: string): string {
		return lang.toLowerCase().split('-')[0];
	}

	/** The device voices whose BCP-47 tag falls under `lang`'s base language. */
	#voicesForLang(lang: string): SpeechSynthesisVoice[] {
		const prefix = this.#langPrefix(lang);
		return this.voices.filter((v) => v.lang.toLowerCase().startsWith(prefix));
	}

	/**
	 * Begin reading `paragraphs` (plain text, in order) from `startAt`.
	 * `opts.media` populates the OS Media Session (lock-screen / background
	 * controls); `opts.onFinish` fires when playback runs off the end on its own
	 * (audiobook roll-over); `opts.onAdvance(index)` fires as each paragraph
	 * begins, driven by the audio — the reader uses it to save the resume point.
	 */
	start(paragraphs: string[], startAt = 0, opts: StartOptions = {}) {
		const lang = opts.lang ?? 'en';
		if (!this.supported) return;
		this.init();
		// If the engine has loaded voices but none the reader would actually speak
		// with resolves for this language, reading would be silent — flag it and
		// bail so the reader can explain, rather than showing a Listen bar that
		// never makes a sound. `resolveVoice` (not a strict language match) is the
		// right predicate: it's exactly what `#speakFrom` uses, so a listener's
		// saved cross-language voice still counts as sound. An empty list means
		// voices haven't loaded yet (not that there are none), so don't warn then.
		if (this.voices.length > 0 && !this.resolveVoice(lang)) {
			this.noVoice = true;
			return;
		}
		this.noVoice = false;
		this.stop();
		this.#paragraphs = paragraphs;
		this.#lang = lang;
		this.total = paragraphs.length;
		this.#media = opts.media ?? null;
		// After stop(), which clears these.
		this.#onFinish = opts.onFinish ?? null;
		this.#onAdvance = opts.onAdvance ?? null;
		this.#setupMedia();
		this.#speakFrom(Math.max(0, Math.min(startAt, paragraphs.length - 1)));
	}

	toggle() {
		if (!this.supported) return;
		if (this.status === 'playing') {
			speechSynthesis.pause();
			this.status = 'paused';
		} else if (this.status === 'paused') {
			speechSynthesis.resume();
			this.status = 'playing';
		}
		this.#mediaState();
	}

	stop() {
		if (!this.supported) return;
		this.#utterance = null; // signal the onend handler this was deliberate
		speechSynthesis.cancel();
		// Same reason as #speakFrom: leave the engine unpaused, or a later
		// start() on another chapter queues into a paused engine and is silent.
		speechSynthesis.resume();
		// The missing-voice notice belongs to the work we were asked to read;
		// stopping (including the stop() the reader fires on navigation) retires
		// it, so it can't linger onto the next page.
		this.noVoice = false;
		// A user stop / navigation is not a natural finish — retire the callbacks so
		// the roll-over can't fire from a deliberate stop and no stray resume-point
		// save lands after we've stopped.
		this.#onFinish = null;
		this.#onAdvance = null;
		this.status = 'idle';
		this.current = -1;
		this.#mediaState();
	}

	skip(delta: number) {
		if (this.status === 'idle') return;
		const next = this.current + delta;
		if (next < 0 || next >= this.#paragraphs.length) return;
		this.#speakFrom(next);
	}

	setRate(rate: number) {
		this.rate = clampRate(rate);
		this.#savePrefs();
		this.#restartCurrent();
	}

	setVoice(voiceURI: string) {
		this.voiceURI = voiceURI;
		this.#savePrefs();
		this.#restartCurrent();
	}

	/**
	 * Speak a short sample in a given voice/rate so the listener can audition it
	 * from the settings panel. Stops any active reading first (SpeechSynthesis is
	 * single-channel) and does NOT enter the paragraph queue, so it leaves the
	 * reader's play state idle rather than showing the Listen bar.
	 */
	preview(sample: string, voiceURI = this.voiceURI, rate = this.rate) {
		if (!this.supported || !sample.trim()) return;
		this.init();
		this.stop();
		const u = new SpeechSynthesisUtterance(sample);
		u.rate = rate;
		// Honour the passed URI if it names a real voice; otherwise audition the
		// language default so the preview matches what reading will actually use.
		const voice = this.resolveVoice(this.#lang, voiceURI);
		if (voice) {
			u.voice = voice;
			u.lang = voice.lang;
		}
		speechSynthesis.speak(u);
	}

	/** Apply a rate/voice change immediately by re-speaking the paragraph. */
	#restartCurrent() {
		if (this.status !== 'idle' && this.current >= 0) this.#speakFrom(this.current);
	}

	#savePrefs() {
		writeJSON(KEY, { rate: this.rate, voiceURI: this.voiceURI });
	}

	#speakFrom(index: number) {
		this.#utterance = null;
		speechSynthesis.cancel();
		// `cancel()` does NOT clear the engine's global `paused` flag, so an
		// utterance queued while paused never starts — and `#speakFrom` sets
		// status='playing' regardless, leaving the bar showing the pause icon
		// and the follow-along highlight moving over silence, with no control
		// short of a reload to recover. Skip and speed/voice changes are all
		// enabled while paused and all route through here.
		speechSynthesis.resume();

		// Skip empty/whitespace-only blocks (images, rules) without recursing.
		while (index < this.#paragraphs.length && !this.#paragraphs[index].trim()) index++;
		if (index >= this.#paragraphs.length) {
			// Reached the end on our own. Capture the finish callback before stop()
			// clears it, then run it — it may start() the next chapter's playback.
			const finished = this.#onFinish;
			this.stop();
			finished?.();
			return;
		}

		const u = new SpeechSynthesisUtterance(this.#paragraphs[index]);
		u.rate = this.rate;
		u.lang = this.#lang;
		const voice = this.resolveVoice(this.#lang);
		if (voice) u.voice = voice;

		u.onend = () => {
			// A deliberate stop()/restart clears #utterance first; only advance
			// when this utterance is still the active one.
			if (this.#utterance !== u) return;
			this.#speakFrom(index + 1);
		};
		u.onerror = () => {
			if (this.#utterance !== u) return;
			this.stop();
		};

		this.#utterance = u;
		this.current = index;
		this.status = 'playing';
		// Resume-point save, bound to the content this start() was given — the
		// audio clock drives it, so it can't race a reactive chapter change.
		this.#onAdvance?.(index);
		this.#mediaState();
		speechSynthesis.speak(u);
	}

	// --- OS Media Session (lock-screen / background / headset controls) --------

	#setupMedia() {
		if (!this.supported || !('mediaSession' in navigator)) return;
		const ms = navigator.mediaSession;
		if (this.#media) {
			try {
				ms.metadata = new MediaMetadata({
					title: this.#media.title,
					artist: this.#media.artist ?? 'Ochorus'
				});
			} catch {
				/* MediaMetadata unavailable — the action handlers below still help */
			}
		}
		if (this.#mediaBound) return; // handlers reference the singleton — bind once
		this.#mediaBound = true;
		const set = (action: MediaSessionAction, handler: () => void) => {
			try {
				ms.setActionHandler(action, handler);
			} catch {
				/* this action isn't supported on this browser */
			}
		};
		set('play', () => this.status === 'paused' && this.toggle());
		set('pause', () => this.status === 'playing' && this.toggle());
		set('previoustrack', () => this.skip(-1));
		set('nexttrack', () => this.skip(1));
		set('stop', () => this.stop());
	}

	#mediaState() {
		if (this.supported && 'mediaSession' in navigator) {
			navigator.mediaSession.playbackState =
				this.status === 'playing' ? 'playing' : this.status === 'paused' ? 'paused' : 'none';
		}
	}

	// --- Sleep timer -----------------------------------------------------------

	/** Auto-stop playback after `minutes` (0 = off). Survives chapter changes. */
	setSleep(minutes: number) {
		this.sleepMinutes = minutes;
		if (this.#sleepTimer) {
			clearTimeout(this.#sleepTimer);
			this.#sleepTimer = null;
		}
		if (minutes > 0) {
			this.#sleepTimer = setTimeout(
				() => {
					this.#sleepTimer = null;
					this.sleepMinutes = 0;
					this.stop();
				},
				minutes * 60_000
			);
		}
	}
}

export const listen = new Listen();
