/**
 * Run `run` once the page has finished loading and the main thread is idle —
 * for work that must not compete with a reader's first taps (mobile INP).
 * Falls back to a 3 s timer where requestIdleCallback is missing (Safari).
 */
export function afterLoadWhenIdle(run: () => void): void {
	const idle = () =>
		'requestIdleCallback' in window
			? requestIdleCallback(run, { timeout: 10_000 })
			: setTimeout(run, 3_000);
	if (document.readyState === 'complete') idle();
	else addEventListener('load', idle, { once: true });
}
