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

export const RATES = [0.8, 1, 1.25, 1.5, 1.75] as const;

const KEY = 'ochorus:listen';

interface Stored {
	rate: number;
	voiceURI: string;
}

function loadPrefs(): Stored {
	const raw = readJSON<{ rate?: number; voiceURI?: unknown }>(KEY, {});
	return {
		rate:
			typeof raw.rate === 'number' && (RATES as readonly number[]).includes(raw.rate)
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

	#paragraphs: string[] = [];
	#lang = 'en';
	#media: { title: string; artist?: string } | null = null;
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

	/** Voices matching the chapter's language, or every voice if none do. */
	get matchingVoices(): SpeechSynthesisVoice[] {
		const prefix = this.#lang.toLowerCase().split('-')[0];
		const match = this.voices.filter((v) => v.lang.toLowerCase().startsWith(prefix));
		return match.length ? match : this.voices;
	}

	/**
	 * Begin reading `paragraphs` (plain text, in order) from `startAt`. `media`
	 * populates the OS Media Session (lock-screen / background controls).
	 */
	start(paragraphs: string[], startAt = 0, lang = 'en', media?: { title: string; artist?: string }) {
		if (!this.supported) return;
		this.init();
		this.stop();
		this.#paragraphs = paragraphs;
		this.#lang = lang;
		this.total = paragraphs.length;
		this.#media = media ?? null;
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
		writeJSON(KEY, { rate: this.rate, voiceURI: this.voiceURI });
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
