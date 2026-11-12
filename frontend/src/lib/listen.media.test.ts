import { describe, it, expect, vi, afterEach } from 'vitest';

/**
 * Listen ⇄ the OS Media Session: the lock screen must show what is being read,
 * its play state must follow Listen's, and its buttons must drive Listen
 * through the same methods as the Listen bar — so a pause on the lock screen
 * leaves the bar, the sleep timer and the resume point consistent. A fake
 * speech engine and a fake `navigator.mediaSession` are installed before the
 * store module loads (it reads `supported` at construction).
 */

class FakeUtterance {
	rate = 1;
	lang = '';
	voice: unknown = null;
	onend: ((e: Event) => void) | null = null;
	onerror: ((e: Event) => void) | null = null;
	text: string;
	constructor(text: string) {
		this.text = text;
	}
}

class FakeMetadata {
	init: MediaMetadataInit;
	constructor(init: MediaMetadataInit) {
		this.init = init;
	}
}

function makeSynth() {
	const state: { last: FakeUtterance | null; paused: boolean } = { last: null, paused: false };
	return {
		state,
		getVoices: () => [
			{ name: 'Test EN', lang: 'en-US', localService: true, default: true, voiceURI: 'test-en' }
		],
		speak(u: FakeUtterance) {
			state.last = u;
		},
		cancel() {},
		resume() {
			state.paused = false;
		},
		pause() {
			state.paused = true;
		},
		addEventListener() {}
	};
}

function makeSession() {
	const handlers = new Map<string, MediaSessionActionHandler | null>();
	const positions: (MediaPositionState | undefined)[] = [];
	const ms = {
		metadata: null as FakeMetadata | null,
		playbackState: 'none',
		setActionHandler: (a: string, h: MediaSessionActionHandler | null) => void handlers.set(a, h),
		setPositionState: (p?: MediaPositionState) => void positions.push(p)
	};
	const fire = (action: string, details: object = {}) =>
		handlers.get(action)?.({ action, ...details } as MediaSessionActionDetails);
	return { ms, handlers, positions, fire };
}

async function fresh({ withSession = true } = {}) {
	vi.resetModules();
	const synth = makeSynth();
	const session = makeSession();
	vi.stubGlobal('speechSynthesis', synth);
	vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance);
	vi.stubGlobal('MediaMetadata', FakeMetadata);
	if (withSession) {
		Object.defineProperty(navigator, 'mediaSession', { value: session.ms, configurable: true });
	}
	const { listen } = await import('./listen.svelte');
	return { listen, synth, session };
}

const end = (synth: ReturnType<typeof makeSynth>) => synth.state.last?.onend?.(new Event('end'));
const MEDIA = {
	title: 'Chapter 2',
	artist: 'Andrew Murray',
	album: 'Humility',
	artwork: ['/covers/humility.png']
};

describe('listen media session', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
		vi.useRealTimers();
		delete (navigator as { mediaSession?: unknown }).mediaSession;
	});

	it('publishes the chapter, book, author and cover when reading starts', async () => {
		const { listen, session } = await fresh();
		listen.start(['One.', 'Two.'], 0, { media: MEDIA });
		const init = (session.ms.metadata as FakeMetadata).init;
		expect(init).toMatchObject({ title: 'Chapter 2', artist: 'Andrew Murray', album: 'Humility' });
		expect(init.artwork?.[0].src).toBe('/covers/humility.png');
		expect(session.ms.playbackState).toBe('playing');
		expect(session.positions.at(-1)).toMatchObject({ position: 0, playbackRate: 1 });
	});

	it('follows pause and resume from the Listen bar, without jumping the clock back', async () => {
		const { listen, session } = await fresh();
		listen.start(['One.', 'Two.'], 0, { media: MEDIA });
		const clocks = session.positions.length;
		listen.toggle();
		expect(session.ms.playbackState).toBe('paused');
		listen.toggle();
		expect(session.ms.playbackState).toBe('playing');
		expect(session.positions.length).toBe(clocks);
	});

	it('lock-screen pause/play drive Listen itself, and a mismatched one is ignored', async () => {
		const { listen, session, synth } = await fresh();
		listen.start(['One.', 'Two.'], 0, { media: MEDIA });
		session.fire('play'); // already playing — must not toggle into a pause
		expect(listen.status).toBe('playing');
		session.fire('pause');
		expect(listen.status).toBe('paused');
		expect(synth.state.paused).toBe(true);
		session.fire('pause'); // already paused — must not resume
		expect(listen.status).toBe('paused');
		session.fire('play');
		expect(listen.status).toBe('playing');
		expect(synth.state.paused).toBe(false);
	});

	it('track, seek and scrub buttons move through the paragraphs', async () => {
		const { listen, session, synth } = await fresh();
		const paras = ['a'.repeat(140), 'b'.repeat(140), 'c'.repeat(140)]; // 10 s each
		listen.start(paras, 0, { media: MEDIA });
		session.fire('nexttrack');
		expect(listen.current).toBe(1);
		expect(session.positions.at(-1)?.position).toBe(10);
		session.fire('seekbackward');
		expect(listen.current).toBe(0);
		session.fire('seekto', { seekTime: 25 });
		expect(listen.current).toBe(2);
		expect(synth.state.last?.text).toBe(paras[2]);
	});

	it('clears the lock screen when reading stops, finishes, or the sleep timer ends it', async () => {
		vi.useFakeTimers();
		const { listen, session, synth } = await fresh();

		listen.start(['One.'], 0, { media: MEDIA });
		listen.stop();
		expect(session.ms.metadata).toBeNull();
		expect(session.ms.playbackState).toBe('none');
		expect(session.handlers.get('play')).toBeNull();

		listen.start(['One.'], 0, { media: MEDIA });
		end(synth); // runs off the end
		expect(session.ms.metadata).toBeNull();

		listen.start(['One.', 'Two.'], 0, { media: MEDIA });
		listen.setSleep(5);
		session.fire('pause'); // paused from the lock screen; the timer still runs
		vi.advanceTimersByTime(5 * 60_000);
		expect(listen.status).toBe('idle');
		expect(listen.sleepMinutes).toBe(0);
		expect(session.ms.metadata).toBeNull();
		expect(session.ms.playbackState).toBe('none');
	});

	it('a stale lock-screen play after a stop does nothing', async () => {
		const { listen, session } = await fresh();
		listen.start(['One.'], 0, { media: MEDIA });
		const play = session.handlers.get('play');
		listen.stop();
		play?.({ action: 'play' } as MediaSessionActionDetails);
		expect(listen.status).toBe('idle');
	});

	it('reads aloud as before where there is no Media Session', async () => {
		const { listen, synth } = await fresh({ withSession: false });
		expect('mediaSession' in navigator).toBe(false);
		listen.start(['One.', 'Two.'], 0, { media: MEDIA });
		expect(listen.status).toBe('playing');
		listen.toggle();
		end(synth);
		listen.stop();
		expect(listen.status).toBe('idle');
	});
});
