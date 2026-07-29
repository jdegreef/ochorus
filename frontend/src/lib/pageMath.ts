/**
 * Which page of a paginated column flow an element sits on.
 *
 * The reader lays the chapter out in CSS columns and turns pages with a
 * translateX. Mapping an element to its page used to be `offsetLeft / pageW`,
 * which silently assumed left-to-right.
 *
 * Under `direction: rtl` the columns overflow LEFT, so `offsetLeft` counts
 * DOWN across the flow — measured on a 1248px page: 656 → 32 → −592 → −1216.
 * The old formula floored those negatives and clamped them to 0, so every page
 * past the first reported as page 0: progress restore, `?p=N` deep links and
 * the bookmark index all landed back on page 1.
 *
 * Measuring the DISTANCE from the flow's first element is direction-agnostic —
 * and in LTR it is arithmetically identical to the old expression, so it is a
 * strict improvement rather than a behaviour change.
 */
export function pageOfOffset(offsetLeft: number, flowOrigin: number, pageW: number): number {
	if (!(pageW > 0)) return 0;
	return Math.floor(Math.abs(offsetLeft - flowOrigin) / pageW);
}
