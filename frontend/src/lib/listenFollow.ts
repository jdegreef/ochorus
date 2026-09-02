/**
 * Read-along scroll policy: should we pull the spoken paragraph into view now?
 *
 * The reader speaks one paragraph per utterance and marks the current one. The
 * old behaviour re-centred it on *every* advance, which (a) fights a reader who
 * has scrolled off to look somewhere else, and (b) jitters the page on a long
 * chapter (76+ blocks). This decides when a scroll is actually warranted:
 *
 *  - **Yield to the hand.** If the reader scrolled themselves within the last
 *    `yieldMs`, leave the page where they put it — following the audio must
 *    never yank it back.
 *  - **Only when off-station.** If the paragraph already sits in a comfortable
 *    reading band — below the sticky header, above the lower fifth — do nothing.
 *    Scroll only when playback has carried it above the header or down past the
 *    fold.
 *
 * Pure so it can be tested without a layout engine; the caller supplies the
 * measured `top` (viewport coordinates) and the viewport/header sizes.
 */
export interface FollowInput {
	/** The spoken paragraph's top edge in viewport coords (getBoundingClientRect().top). */
	top: number;
	viewportHeight: number;
	/** Height of the sticky reader header the paragraph must clear. */
	headerOffset: number;
	/** Milliseconds since the reader last scrolled by hand (Infinity if never). */
	msSinceUserScroll: number;
	yieldMs: number;
}

/** Padding below the header so the paragraph's start clears the chrome. */
const BAND_TOP_PAD = 8;
/** Bottom of the comfortable band, as a fraction of the viewport height. */
const BAND_BOTTOM_FRACTION = 0.8;

export function shouldFollow(i: FollowInput): boolean {
	if (i.msSinceUserScroll < i.yieldMs) return false;
	const bandTop = i.headerOffset + BAND_TOP_PAD;
	const bandBottom = i.viewportHeight * BAND_BOTTOM_FRACTION;
	return i.top < bandTop || i.top > bandBottom;
}
