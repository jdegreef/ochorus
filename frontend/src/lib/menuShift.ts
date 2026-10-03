/**
 * Places a dropdown hung from a button so it stays on screen on a phone.
 *
 * Placed from the BUTTON, not by measuring the menu: on a phone the button
 * can wrap to mid-row, where a menu hung from it runs off the screen (and
 * scrolls the page sideways), and a menu measured as it opens is measured
 * before its contents have laid out. So the menu gets a known width — at most
 * `maxWidth`, never wider than the screen less `gutter` a side — and is slid
 * from where it would hang (the button's inline start or end edge) just
 * enough to stay inside the screen.
 *
 * Returns the width and the PHYSICAL `left` offset relative to the button's
 * containing box (the menu's `position: relative` parent shares the button's
 * left edge), so the caller sets `style:left` / `style:width` and clears the
 * logical insets. Screen pixels, so the same in RTL.
 */
export function menuShift(
	anchor: Element,
	maxWidth: number,
	align: 'start' | 'end' = 'start',
	gutter = 8
): { width: number; shift: number } {
	const vw = document.documentElement.clientWidth;
	const btn = anchor.getBoundingClientRect();
	const width = Math.max(0, Math.min(maxWidth, vw - gutter * 2));
	const rtl = getComputedStyle(anchor).direction === 'rtl';
	// Hang from the left edge for start-in-LTR / end-in-RTL, else the right.
	const fromLeft = (align === 'start') !== rtl;
	const desired = fromLeft ? btn.left : btn.right - width;
	const left = Math.min(Math.max(desired, gutter), vw - gutter - width);
	return { width, shift: left - btn.left };
}
