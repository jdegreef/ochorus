import { describe, it, expect, vi, afterEach } from 'vitest';
import {
	CHARS_PER_SECOND,
	MEDIA_ACTIONS,
	bindMediaSession,
	estimatePosition,
	mediaArtwork,
	mediaMetadataInit,
	paragraphAt,
	unbindMediaSession
} from './listenMedia';

/** A stand-in Media Session that records what was set on it. */
export function fakeMediaSession() {
	const handlers = new Map<string, MediaSessionActionHandler | null>();
	const positions: (MediaPositionState | undefined)[] = [];
	const ms = {
		metadata: null as MediaMetadata | null,
		playbackState: 'none' as MediaSessionPlaybackState,
		setActionHandler(action: string, h: MediaSessionActionHandler | null) {
			if (action === 'seekto' && ms.rejectSeekTo) throw new TypeError('unsupported');
			handlers.set(action, h);
		},
		setPositionState(p?: MediaPositionState) {
			positions.push(p);
		},
		rejectSeekTo: false
	};
	const fire = (action: string, details: Partial<MediaSessionActionDetails> = {}) =>
		handlers.get(action)?.({ action, ...details } as MediaSessionActionDetails);
	return { ms, handlers, positions, fire };
}

const text = (seconds: number) => 'x'.repeat(seconds * CHARS_PER_SECOND);

describe('mediaArtwork', () => {
	it('keeps rasters best-first, drops plates and repeats, and ends on the house icon', () => {
		const art = mediaArtwork([
			'/covers/humility.png',
			null,
			'/covers/humility-640.webp',
			'/covers/humility.png',
			'/covers/fr/humility.svg',
			'/og/covers/en/humility.jpg'
		]);
		expect(art.map((a) => a.src)).toEqual([
			'/covers/humility.png',
			'/covers/humility-640.webp',
			'/og/covers/en/humility.jpg',
			'/icons/icon-192.png',
			'/icons/icon-512.png'
		]);
		expect(art[0].type).toBe('image/png');
		expect(art[1].type).toBe('image/webp');
		expect(art[2]).toMatchObject({ type: 'image/jpeg', sizes: '1200x630' });
		// A cover variant's real width varies, so it claims no size.
		expect(art[1].sizes).toBeUndefined();
	});

	it('still offers the house icon when the work has no picture', () => {
		expect(mediaArtwork().map((a) => a.sizes)).toEqual(['192x192', '512x512']);
	});
});

describe('mediaMetadataInit', () => {
	it('names the chapter, author and book', () => {
		const m = mediaMetadataInit({ title: 'Chapter 3', artist: 'Andrew Murray', album: 'Humility' });
		expect(m).toMatchObject({ title: 'Chapter 3', artist: 'Andrew Murray', album: 'Humility' });
		expect(m.artwork?.length).toBe(2);
	});

	it('falls back to the house name when there is no author', () => {
		expect(mediaMetadataInit({ title: 'An article' })).toMatchObject({ artist: 'Ochorus', album: '' });
	});
});

describe('estimatePosition / paragraphAt', () => {
	const paras = [text(10), '', text(20), text(30)];

	it('times the reading from its length, at rate 1 media seconds', () => {
		expect(estimatePosition(paras, 0, 1)).toEqual({ duration: 60, position: 0, playbackRate: 1 });
		expect(estimatePosition(paras, 2, 1.5)).toEqual({ duration: 60, position: 10, playbackRate: 1.5 });
		expect(estimatePosition(paras, 3, 1)?.position).toBe(30);
	});

	it('has no clock for nothing to read', () => {
		expect(estimatePosition([], 0, 1)).toBeNull();
		expect(estimatePosition(['  '], 0, 1)).toBeNull();
	});

	it('maps a scrub back to the paragraph that holds that time, skipping blanks', () => {
		expect(paragraphAt(paras, 0)).toBe(0);
		expect(paragraphAt(paras, 9)).toBe(0);
		expect(paragraphAt(paras, 10)).toBe(2);
		expect(paragraphAt(paras, 45)).toBe(3);
		expect(paragraphAt(paras, 999)).toBe(3);
	});
});

describe('bindMediaSession', () => {
	afterEach(() => vi.restoreAllMocks());

	function controls() {
		return { play: vi.fn(), pause: vi.fn(), stop: vi.fn(), skip: vi.fn(), seekTo: vi.fn() };
	}

	it('maps each OS action to a Listen control', () => {
		const { ms, fire } = fakeMediaSession();
		const c = controls();
		bindMediaSession(ms as unknown as MediaSession, c);
		fire('play');
		fire('pause');
		fire('stop');
		expect([c.play, c.pause, c.stop].map((f) => f.mock.calls.length)).toEqual([1, 1, 1]);
		fire('nexttrack');
		fire('seekforward');
		fire('previoustrack');
		fire('seekbackward');
		expect(c.skip.mock.calls).toEqual([[1], [1], [-1], [-1]]);
		fire('seekto', { seekTime: 42 });
		fire('seekto', {}); // no time given — ignored
		expect(c.seekTo.mock.calls).toEqual([[42]]);
	});

	it('survives a browser that rejects an action it does not know', () => {
		const { ms, handlers } = fakeMediaSession();
		ms.rejectSeekTo = true;
		expect(() => bindMediaSession(ms as unknown as MediaSession, controls())).not.toThrow();
		expect(handlers.has('play')).toBe(true);
		expect(handlers.has('seekto')).toBe(false);
	});

	it('unbinding retires every handler, the metadata and the clock', () => {
		const { ms, handlers, positions } = fakeMediaSession();
		bindMediaSession(ms as unknown as MediaSession, controls());
		ms.metadata = {} as MediaMetadata;
		ms.playbackState = 'playing';
		unbindMediaSession(ms as unknown as MediaSession);
		for (const a of MEDIA_ACTIONS) expect(handlers.get(a) ?? null).toBeNull();
		expect(ms.metadata).toBeNull();
		expect(ms.playbackState).toBe('none');
		expect(positions.at(-1)).toBeUndefined();
	});
});
