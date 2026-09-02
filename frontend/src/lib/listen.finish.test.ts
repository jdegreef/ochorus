import { describe, it, expect, vi, afterEach } from 'vitest';

/**
 * The `onFinish` hook drives audiobook roll-over: it must fire exactly once when
 * playback runs off the end on its own, and never on a user stop. Verified with
 * a fake speech engine installed BEFORE the store module loads (its `supported`
 * flag is read at construction), whose `speak` records the utterance without
 * ending it — so the test advances paragraph-by-paragraph by hand.
 */

class FakeUtterance {
	text: string;
	rate = 1;
	lang = '';
	voice: unknown = null;
	onend: ((e: Event) => void) | null = null;
	onerror: ((e: Event) => void) | null = null;
	constructor(text: string) {
		this.text = text;
	}
}

function makeSynth() {
	const state: { last: FakeUtterance | null } = { last: null };
	return {
		state,
		getVoices: () => [
			{ name: 'Test EN', lang: 'en-US', localService: true, default: true, voiceURI: 'test-en' }
		],
		speak(u: FakeUtterance) {
			state.last = u; // hold it; the test ends it explicitly
		},
		cancel() {},
		resume() {},
		pause() {},
		addEventListener() {},
		removeEventListener() {}
	};
}

async function freshListen() {
	vi.resetModules();
	const synth = makeSynth();
	vi.stubGlobal('speechSynthesis', synth);
	vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance);
	const mod = await import('./listen.svelte');
	return { listen: mod.listen, synth };
}

/** Fire the pending utterance's onend — advances to the next paragraph. */
function endParagraph(synth: ReturnType<typeof makeSynth>) {
	synth.state.last?.onend?.(new Event('end'));
}

describe('listen onFinish (audiobook roll-over hook)', () => {
	afterEach(() => vi.unstubAllGlobals());

	it('fires onFinish once when playback runs off the end', async () => {
		const { listen, synth } = await freshListen();
		const cb = vi.fn();
		listen.start(['one', 'two', 'three'], 0, 'en', { title: 't' }, cb);
		expect(listen.status).toBe('playing');
		endParagraph(synth); // -> two
		endParagraph(synth); // -> three
		expect(cb).not.toHaveBeenCalled();
		endParagraph(synth); // -> past the end
		expect(cb).toHaveBeenCalledTimes(1);
		expect(listen.status).toBe('idle');
	});

	it('does not fire onFinish on a user stop mid-chapter', async () => {
		const { listen, synth } = await freshListen();
		const cb = vi.fn();
		listen.start(['a', 'b', 'c', 'd'], 0, 'en', { title: 't' }, cb);
		endParagraph(synth); // -> b
		listen.stop();
		expect(cb).not.toHaveBeenCalled();
		expect(listen.status).toBe('idle');
	});

	it('does not carry a finish callback from a stopped run into the next', async () => {
		const { listen, synth } = await freshListen();
		const first = vi.fn();
		listen.start(['a', 'b'], 0, 'en', { title: 't' }, first);
		listen.stop(); // retires `first`
		// A second run with no callback must not resurrect the first one.
		listen.start(['x', 'y'], 0, 'en', { title: 't' });
		endParagraph(synth); // -> y
		endParagraph(synth); // -> past the end
		expect(first).not.toHaveBeenCalled();
		expect(listen.status).toBe('idle');
	});
});
