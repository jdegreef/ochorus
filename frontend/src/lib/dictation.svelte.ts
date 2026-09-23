import { browser } from '$app/environment';

/**
 * Speak instead of type — the browser's own speech recognition (Chrome,
 * Edge, Safari; not Firefox). Where it isn't available `supported` is false
 * and callers simply don't offer it. Recognition runs in the browser's speech
 * service (Chrome sends audio to Google's), which is why the button says so.
 *
 * One session at a time: starting a new one stops the last. Final phrases are
 * handed to `onText` as they settle; the in-progress one is `interim`.
 */

interface RecognitionResult {
	isFinal: boolean;
	0: { transcript: string };
}
interface RecognitionEvent {
	resultIndex: number;
	results: ArrayLike<RecognitionResult>;
}
interface Recognition {
	lang: string;
	continuous: boolean;
	interimResults: boolean;
	onresult: ((e: RecognitionEvent) => void) | null;
	onend: (() => void) | null;
	onerror: (() => void) | null;
	start(): void;
	stop(): void;
}
type RecognitionCtor = new () => Recognition;

const Ctor: RecognitionCtor | undefined = browser
	? ((window as unknown as { SpeechRecognition?: RecognitionCtor }).SpeechRecognition ??
		(window as unknown as { webkitSpeechRecognition?: RecognitionCtor }).webkitSpeechRecognition)
	: undefined;

class Dictation {
	readonly supported = !!Ctor;
	listening = $state(false);
	interim = $state('');
	#rec: Recognition | null = null;

	start(lang: string, onText: (text: string) => void) {
		if (!Ctor) return;
		this.stop();
		const rec = new Ctor();
		rec.lang = lang;
		rec.continuous = true;
		rec.interimResults = true;
		rec.onresult = (e) => {
			let interim = '';
			for (let i = e.resultIndex; i < e.results.length; i++) {
				const r = e.results[i];
				if (r.isFinal) onText(r[0].transcript.trim());
				else interim += r[0].transcript;
			}
			this.interim = interim;
		};
		rec.onend = rec.onerror = () => {
			if (this.#rec === rec) this.#reset();
		};
		this.#rec = rec;
		this.listening = true;
		try {
			rec.start();
		} catch {
			this.#reset();
		}
	}

	stop() {
		this.#rec?.stop();
		this.#reset();
	}

	#reset() {
		this.#rec = null;
		this.listening = false;
		this.interim = '';
	}
}

export const dictation = new Dictation();
