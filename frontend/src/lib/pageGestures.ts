/**
 * Pure geometry for the reader's page-turn gestures — tap zones, swipe release
 * and the rubber-band on a live drag. Kept out of the reader component so the
 * direction/threshold logic is unit-testable without a DOM: the pointer gestures
 * (tap + swipe) resolve their physical→logical "which way is next" flip here,
 * with a test, rather than in scattered `x < 0.15` literals. (The keyboard and
 * edge-arrow handlers still flip inline against `contentRtl` — they turn on a
 * fixed direction, not a measured position, so they never needed the geometry.)
 *
 * Everything here is PHYSICAL — `x`/`dx` are screen pixels, left-positive — and
 * `rtl` names the CONTENT direction (an Arabic book pages right-to-left even
 * under an English shell). Callers translate the returned Turn into the reader's
 * own `pageIndex` delta, where +1 is always "later in the book" regardless of
 * script (the RTL flip lives in the CSS transform, see the reader).
 */

export type Turn = 'next' | 'prev' | 'none';

/**
 * Which page a tap at horizontal position `x` (px from the left edge of a
 * `width`-wide viewport) turns to, splitting the screen into a left and a right
 * zone. `deadZone` (0..1) is the width of a neutral centre band that turns
 * nothing: 0 is a clean 50/50 split (touch — the whole screen is a page-turn),
 * 0.7 leaves only the outer 15% live on each side (desktop, where a click in the
 * body is for selecting, and the edge arrows are the real affordance).
 *
 * In RTL the reading advances right-to-left, so the LEFT zone is "next".
 */
export function tapTurn(x: number, width: number, rtl: boolean, deadZone = 0): Turn {
	if (width <= 0) return 'none';
	const f = x / width;
	const lo = 0.5 - deadZone / 2;
	const hi = 0.5 + deadZone / 2;
	if (f <= lo) return rtl ? 'next' : 'prev';
	if (f >= hi) return rtl ? 'prev' : 'next';
	return 'none';
}

/**
 * Which page-turn a horizontal swipe commits to on release. `dx` is the net
 * horizontal travel and `dy` the vertical; a swipe more vertical than horizontal
 * is a scroll, not a turn, and one shorter than `minRatio` of the viewport width
 * is an accidental nudge that should snap back. A leftward swipe (dx<0) advances
 * in LTR; RTL flips it.
 */
export function swipeTurn(
	dx: number,
	dy: number,
	width: number,
	rtl: boolean,
	minRatio = 0.18
): Turn {
	if (width <= 0) return 'none';
	if (Math.abs(dx) <= Math.abs(dy)) return 'none';
	if (Math.abs(dx) < width * minRatio) return 'none';
	const advance = rtl ? dx > 0 : dx < 0;
	return advance ? 'next' : 'prev';
}

/**
 * Damp a live drag offset so the first and last pages of a chapter resist
 * instead of sliding a blank gutter into view: full travel in range, a fraction
 * of it once the drag is pulling past the edge. `atFirst`/`atLast` are the page
 * bounds; the physical direction that pulls past them flips under `rtl`. A firm
 * swipe can still roll over to the adjacent chapter — that decision is made from
 * the raw travel on release (see swipeTurn), not from this damped value.
 */
export function dampDrag(
	dx: number,
	atFirst: boolean,
	atLast: boolean,
	rtl: boolean,
	factor = 0.35
): number {
	const advancing = rtl ? dx > 0 : dx < 0; // toward a later page
	const receding = rtl ? dx < 0 : dx > 0; // toward an earlier page
	const beyond = (advancing && atLast) || (receding && atFirst);
	return beyond ? dx * factor : dx;
}
