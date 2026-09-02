import { describe, it, expect, beforeEach } from 'vitest';
import { listen } from './listen.svelte';

// SpeechSynthesis isn't in jsdom, so these exercise the pure voice-resolution
// logic directly by seeding `listen.voices` — the part a device can't vary.
function voice(name: string, lang: string, localService = false): SpeechSynthesisVoice {
	return { name, lang, localService, default: false, voiceURI: name } as SpeechSynthesisVoice;
}

const GOOGLE_UK_MALE = voice('Google UK English Male', 'en-GB');
const GOOGLE_US = voice('Google US English', 'en-US');
const SAMANTHA = voice('Samantha', 'en-US', true);
const SPANISH = voice('Google español', 'es-ES');

describe('listen voice defaults', () => {
	beforeEach(() => {
		listen.voiceURI = '';
	});

	it('defaults English to Google UK English Male when present', () => {
		listen.voices = [GOOGLE_US, GOOGLE_UK_MALE, SAMANTHA];
		expect(listen.defaultVoice('en')?.name).toBe('Google UK English Male');
		expect(listen.resolveVoice('en')?.name).toBe('Google UK English Male');
	});

	it('falls back to the top device voice where the preferred one is absent', () => {
		listen.voices = [SAMANTHA, GOOGLE_US];
		// No Google UK English Male installed (Safari/iOS): pick the best available.
		expect(listen.defaultVoice('en')?.name).toBe('Google US English');
	});

	it('leaves languages without a preferred default to the top device voice', () => {
		listen.voices = [SPANISH, SAMANTHA];
		expect(listen.defaultVoice('es')?.name).toBe('Google español');
	});

	it("honours the listener's explicit choice over the default", () => {
		listen.voices = [GOOGLE_UK_MALE, SAMANTHA];
		listen.voiceURI = 'Samantha';
		expect(listen.resolveVoice('en')?.name).toBe('Samantha');
	});

	it('resolves the default when the saved voice is no longer installed', () => {
		listen.voices = [GOOGLE_UK_MALE, GOOGLE_US];
		listen.voiceURI = 'A Voice From Another Device';
		expect(listen.resolveVoice('en')?.name).toBe('Google UK English Male');
	});

	it('leads topVoices with the preferred default so the picker matches the reading voice', () => {
		// Google UK English Male listed last, yet it must sort to the front — the
		// Settings dropdown highlights voices[0], and that must equal defaultVoice.
		listen.voices = [GOOGLE_US, SAMANTHA, GOOGLE_UK_MALE];
		const top = listen.topVoices('en', 4);
		expect(top[0]?.name).toBe('Google UK English Male');
		expect(top[0]?.name).toBe(listen.defaultVoice('en')?.name);
	});
});

// The missing-voice notice fires when nothing the reader would actually speak
// with resolves for the language — i.e. the same `resolveVoice` predicate the
// `start()` guard uses. These pin that predicate so the guard can't drift.
describe('listen missing-voice predicate', () => {
	beforeEach(() => {
		listen.voiceURI = '';
		listen.noVoice = false;
	});

	it('resolves nothing when the device lacks the language and no voice is saved', () => {
		listen.voices = [GOOGLE_US, SAMANTHA]; // English only
		expect(listen.resolveVoice('sw')).toBeUndefined();
		expect(listen.resolveVoice('lg')).toBeUndefined();
	});

	it('still resolves a saved cross-language voice, so playback is not silent', () => {
		// A listener whose saved English voice is installed must NOT be warned
		// off a Swahili book — reading it aloud in that voice makes sound.
		listen.voices = [GOOGLE_US, SAMANTHA];
		listen.voiceURI = 'Samantha';
		expect(listen.resolveVoice('sw')?.name).toBe('Samantha');
	});

	it('dismissNoVoice clears the notice', () => {
		listen.noVoice = true;
		listen.dismissNoVoice();
		expect(listen.noVoice).toBe(false);
	});
});
