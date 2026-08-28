/**
 * Test stand-in for SvelteKit's `$app/navigation`.
 *
 * Only `preloadCode` so far: `offlineBooks.download()` warms the chapter
 * route's own module so a downloaded book can be opened offline without having
 * been read online first (#1140). Recording the calls is what lets that be
 * asserted — the real function does a dynamic import the test cannot see.
 */
export const preloaded: string[] = [];

let fails = false;
/** Make the next `preloadCode` reject, to exercise the caller's fallback. */
export function setPreloadFails(v: boolean): void {
	fails = v;
}

export async function preloadCode(pathname: string): Promise<void> {
	if (fails) throw new Error('module unavailable');
	preloaded.push(pathname);
}
