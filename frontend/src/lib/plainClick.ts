/**
 * "Is this click the reader asking us to handle it in place?" — the check a
 * link's click handler makes before claiming the click. A modified click
 * (cmd/ctrl/shift/alt) or a non-primary button is the reader asking for a new
 * tab or window, so it is left to the browser.
 *
 * Import-free on purpose: coverFlight.ts is in the root layout's static import
 * closure, which has a bundle budget (frontend/CLAUDE.md).
 */

type ClickLike = Pick<
	MouseEvent,
	'button' | 'metaKey' | 'ctrlKey' | 'shiftKey' | 'altKey' | 'defaultPrevented'
>;

/** A primary-button click with no modifier key. Says nothing about whether
 *  another handler already claimed it — see {@link isPlainPrimaryClick}. */
export function isUnmodifiedPrimaryClick(e: Omit<ClickLike, 'defaultPrevented'>): boolean {
	return e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;
}

/** A primary-button click with no modifier key that no handler has already
 *  claimed (`preventDefault`). */
export function isPlainPrimaryClick(e: ClickLike): boolean {
	return !e.defaultPrevented && isUnmodifiedPrimaryClick(e);
}
