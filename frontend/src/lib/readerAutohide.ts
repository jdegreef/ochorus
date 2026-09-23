/**
 * Should the reader's top bar be hidden after a scroll event?
 *
 * The reader auto-hides its top bar as you read down and brings it back the
 * moment you scroll up or reach the top, so the prose gets more of the screen
 * without a mode to discover. The decision is pure — separated from the DOM so
 * the direction rules (and their thresholds) can be tested without a rendered
 * reader.
 *
 * Rules, in order:
 * - a jump larger than a viewport is programmatic (restore-scroll, a deep link,
 *   a chapter open), not a read gesture — leave the bar as it was;
 * - near the very top, or scrolling up, always show;
 * - scrolling down past a small deadzone, hide;
 * - a sub-deadzone wobble changes nothing.
 */
const DEADZONE = 6;

export function nextBarHidden(
	current: boolean,
	scrollY: number,
	lastScrollY: number,
	innerHeight: number,
	revealWithin = 72
): boolean {
	const dy = scrollY - lastScrollY;
	if (Math.abs(dy) > innerHeight) return current;
	if (scrollY <= revealWithin || dy < -DEADZONE) return false;
	if (dy > DEADZONE) return true;
	return current;
}
