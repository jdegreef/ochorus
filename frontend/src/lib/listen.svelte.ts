import { browser } from '$app/environment';

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

export const RATES = [0.8, 1, 1.25, 1.5, 1.75] as const;

const KEY = 'ochorus:listen';

interface Stored {
	rate: number;
	voiceURI: string;
}

function loadPrefs(): Stored {
	if (!browser) return { rate: 1, voiceURI: '' };
	try {
		const raw = JSON.parse(localStorage.getItem(KEY) || '{}');
		return {
			rate: RATES.includes(raw.rate) ? raw.rate : 1,
			voiceURI: typeof raw.voiceURI === 'string' ? raw.voiceURI : ''
		};
	} catch {
		return { rate: 1, voiceURI: '' };
	}
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

	#paragraphs: string[] = [];
	#lang = 'en';
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

	/** Voices matching the chapter's language, or every voice if none do. */
	get matchingVoices(): SpeechSynthesisVoice[] {
		const prefix = this.#lang.toLowerCase().split('-')[0];
		const match = this.voices.filter((v) => v.lang.toLowerCase().startsWith(prefix));
		return match.length ? match : this.voices;
	}

	/** Begin reading `paragraphs` (plain text, in order) from `startAt`. */
	start(paragraphs: string[], startAt = 0, lang = 'en') {
		if (!this.supported) return;
		this.init();
		this.stop();
		this.#paragraphs = paragraphs;
		this.#lang = lang;
		this.total = paragraphs.length;
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
	}

	stop() {
		if (!this.supported) return;
		this.#utterance = null; // signal the onend handler this was deliberate
		speechSynthesis.cancel();
		this.status = 'idle';
		this.current = -1;
	}

	skip(delta: number) {
		if (this.status === 'idle') return;
		const next = this.current + delta;
		if (next < 0 || next >= this.#paragraphs.length) return;
		this.#speakFrom(next);
	}

	setRate(rate: number) {
		this.rate = rate;
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
		const voice = this.voices.find((v) => v.voiceURI === voiceURI);
		if (voice) {
			u.voice = voice;
			u.lang = voice.lang;
		}
		speechSynthesis.speak(u);
	}

	/** All available voices grouped by BCP-47 language tag, for a settings picker. */
	get voicesByLang(): { lang: string; voices: SpeechSynthesisVoice[] }[] {
		const groups = new Map<string, SpeechSynthesisVoice[]>();
		for (const v of this.voices) {
			const list = groups.get(v.lang) ?? [];
			list.push(v);
			groups.set(v.lang, list);
		}
		return [...groups.entries()]
			.map(([lang, voices]) => ({ lang, voices: voices.sort((a, b) => a.name.localeCompare(b.name)) }))
			.sort((a, b) => a.lang.localeCompare(b.lang));
	}

	/** Apply a rate/voice change immediately by re-speaking the paragraph. */
	#restartCurrent() {
		if (this.status !== 'idle' && this.current >= 0) this.#speakFrom(this.current);
	}

	#savePrefs() {
		if (!browser) return;
		localStorage.setItem(KEY, JSON.stringify({ rate: this.rate, voiceURI: this.voiceURI }));
	}

	#speakFrom(index: number) {
		this.#utterance = null;
		speechSynthesis.cancel();

		// Skip empty/whitespace-only blocks (images, rules) without recursing.
		while (index < this.#paragraphs.length && !this.#paragraphs[index].trim()) index++;
		if (index >= this.#paragraphs.length) {
			this.stop();
			return;
		}

		const u = new SpeechSynthesisUtterance(this.#paragraphs[index]);
		u.rate = this.rate;
		u.lang = this.#lang;
		const voice = this.voices.find((v) => v.voiceURI === this.voiceURI);
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
		speechSynthesis.speak(u);
	}
}

export const listen = new Listen();
