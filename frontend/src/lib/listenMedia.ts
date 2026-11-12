/**
 * Listen's face outside the page: the OS Media Session — the lock screen,
 * notification shade, Control Centre, headset and keyboard media keys.
 *
 * Kept apart from `listen.svelte.ts` so the pieces a device can't vary — what
 * the metadata says, which artwork it offers, where the estimated clock stands,
 * which handler maps to which Listen control — are testable without a speech
 * engine, and so `listen` only says WHEN to publish, never HOW.
 *
 * What a reader actually sees depends on the browser, not on us. Listen speaks
 * through `speechSynthesis`, and Chrome, Safari and Firefox only surface a
 * media session for a page that is playing a media element — speech alone does
 * not claim one. So everything here is feature-detected and best-effort: where
 * the platform shows it, it is right (cover, chapter, book, author, a clock,
 * pause/skip that keep Listen's own state); where it doesn't, it is a no-op.
 * Android's app web view has no `navigator.mediaSession` at all. See the
 * "Listen outside the page" note in MOBILE.md for the per-platform picture.
 */
import { assetUrl } from '$lib/assetUrl';

/** What Listen is reading, as the OS should name it. Image paths are SITE
 *  paths (`/covers/…`, `/og/…`); they are resolved for the app here. */
export interface ListenMedia {
	/** The chapter / sermon / article title. */
	title: string;
	/** Who wrote it. */
	artist?: string;
	/** The book a chapter belongs to. */
	album?: string;
	/** Candidate artwork, best first; the house icon is always appended. */
	artwork?: (string | null | undefined)[];
}

/** The house mark, at the sizes manifest.json declares — the artwork of last
 *  resort, so a lock screen never shows a blank square. */
const HOUSE_ICONS: MediaImage[] = [
	{ src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
	{ src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' }
];

/** Known pixel sizes, by path shape, so the OS can pick without fetching. The
 *  cover variants' real widths vary (the builder never upscales), so those
 *  claim nothing rather than something untrue. */
function sizeOf(path: string): string | undefined {
	if (path.startsWith('/og/covers/')) return '1200x630';
	if (path.startsWith('/og/sermons/')) return '1200x630';
	return undefined;
}

function typeOf(path: string): string | undefined {
	const ext = path.replace(/[?#].*$/, '').split('.').pop()?.toLowerCase();
	return ext === 'png'
		? 'image/png'
		: ext === 'jpg' || ext === 'jpeg'
			? 'image/jpeg'
			: ext === 'webp'
				? 'image/webp'
				: undefined;
}

/**
 * The Media Session artwork list: each distinct candidate (an `.svg` plate is
 * dropped — several OS surfaces cannot paint one), resolved for this build,
 * then the house icons.
 */
export function mediaArtwork(paths: (string | null | undefined)[] = []): MediaImage[] {
	const seen = new Set<string>();
	const out: MediaImage[] = [];
	for (const p of paths) {
		if (!p || p.endsWith('.svg') || seen.has(p)) continue;
		seen.add(p);
		const img: MediaImage = { src: assetUrl(p) };
		const sizes = sizeOf(p);
		const type = typeOf(p);
		if (sizes) img.sizes = sizes;
		if (type) img.type = type;
		out.push(img);
	}
	return [...out, ...HOUSE_ICONS];
}

/** The `MediaMetadata` init for a reading. */
export function mediaMetadataInit(media: ListenMedia): MediaMetadataInit {
	return {
		title: media.title,
		artist: media.artist || 'Ochorus',
		album: media.album ?? '',
		artwork: mediaArtwork(media.artwork)
	};
}

/**
 * Characters a voice speaks per second at rate 1 — about 150 words a minute.
 * Speech synthesis reports no duration, so Listen's clock is an ESTIMATE from
 * the text's length; it is what the lock screen's scrubber and "time left"
 * show, and it is only ever as good as this average.
 */
export const CHARS_PER_SECOND = 14;

/** Seconds of speech in `text` at rate 1. */
const secondsOf = (text: string) => text.trim().length / CHARS_PER_SECOND;

/**
 * Where an estimated clock stands at the START of paragraph `current`: the
 * reading's whole length and the time already passed, both in media seconds
 * (rate 1 — the OS divides by `playbackRate` itself). Null when there is
 * nothing to time.
 */
export function estimatePosition(
	paragraphs: string[],
	current: number,
	rate: number
): MediaPositionState | null {
	let duration = 0;
	let position = 0;
	paragraphs.forEach((p, i) => {
		const s = secondsOf(p);
		duration += s;
		if (i < current) position += s;
	});
	if (!(duration > 0) || !(rate > 0)) return null;
	const round = (n: number) => Math.round(n * 10) / 10;
	duration = round(duration);
	return { duration, position: Math.min(round(position), duration), playbackRate: rate };
}

/** The paragraph a seek to `seconds` lands in (the inverse of
 *  `estimatePosition`): the last one that starts at or before it. */
export function paragraphAt(paragraphs: string[], seconds: number): number {
	let t = 0;
	let last = 0;
	for (let i = 0; i < paragraphs.length; i++) {
		if (!paragraphs[i].trim()) continue;
		if (t > seconds) break;
		last = i;
		t += secondsOf(paragraphs[i]);
	}
	return last;
}

/** Listen's controls, as the OS action handlers call them. */
export interface MediaControls {
	play: () => void;
	pause: () => void;
	stop: () => void;
	/** Move by `delta` paragraphs. */
	skip: (delta: number) => void;
	/** Jump to an estimated time, in seconds. */
	seekTo: (seconds: number) => void;
}

/** Every action Listen answers, so `unbindMediaSession` can clear them all. */
export const MEDIA_ACTIONS: MediaSessionAction[] = [
	'play',
	'pause',
	'stop',
	'previoustrack',
	'nexttrack',
	'seekbackward',
	'seekforward',
	'seekto'
];

/** The navigator's Media Session, or null where there is none (Android's
 *  app web view, older browsers, the prerender). */
export function mediaSession(): MediaSession | null {
	return typeof navigator !== 'undefined' && 'mediaSession' in navigator
		? navigator.mediaSession
		: null;
}

/** Set one handler, swallowing the throw a browser gives an action it doesn't
 *  know (an older Safari has no `seekto`). */
function setHandler(
	ms: MediaSession,
	action: MediaSessionAction,
	handler: MediaSessionActionHandler | null
) {
	try {
		ms.setActionHandler(action, handler);
	} catch {
		/* this action isn't supported here */
	}
}

/**
 * Wire the OS controls to Listen. Track and seek buttons both move by a
 * paragraph — a lock screen shows one pair or the other, and either way the
 * reader means "the next bit". A scrub (`seekto`) lands on the paragraph that
 * holds that time.
 */
export function bindMediaSession(ms: MediaSession, c: MediaControls) {
	setHandler(ms, 'play', () => c.play());
	setHandler(ms, 'pause', () => c.pause());
	setHandler(ms, 'stop', () => c.stop());
	setHandler(ms, 'previoustrack', () => c.skip(-1));
	setHandler(ms, 'nexttrack', () => c.skip(1));
	setHandler(ms, 'seekbackward', () => c.skip(-1));
	setHandler(ms, 'seekforward', () => c.skip(1));
	setHandler(ms, 'seekto', (d) => {
		if (typeof d.seekTime === 'number') c.seekTo(d.seekTime);
	});
}

/** Retire every handler and the metadata — nothing is playing any more. */
export function unbindMediaSession(ms: MediaSession) {
	for (const a of MEDIA_ACTIONS) setHandler(ms, a, null);
	ms.metadata = null;
	ms.playbackState = 'none';
	try {
		ms.setPositionState?.();
	} catch {
		/* no position state to clear */
	}
}

/** Publish the metadata. `MediaMetadata` can be missing where the session is
 *  not (or throw on an artwork URL it dislikes); the handlers still help then. */
export function publishMetadata(ms: MediaSession, media: ListenMedia) {
	try {
		ms.metadata = new MediaMetadata(mediaMetadataInit(media));
	} catch {
		/* MediaMetadata unavailable */
	}
}

/** Publish the play state and, where it can be estimated, the clock. */
export function publishState(
	ms: MediaSession,
	status: 'idle' | 'playing' | 'paused',
	position: MediaPositionState | null
) {
	ms.playbackState = status === 'playing' ? 'playing' : status === 'paused' ? 'paused' : 'none';
	if (!position || !ms.setPositionState) return;
	try {
		ms.setPositionState(position);
	} catch {
		/* a browser that rejects the estimate keeps its own idea of the clock */
	}
}
