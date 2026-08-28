/**
 * Fail loudly when the DOM environment the store tests rely on is not the one
 * jsdom was asked for.
 *
 * WHY THIS EXISTS. Node 25 ships Web Storage ON by default, so `globalThis`
 * carries a `localStorage` of its own. Without `--localstorage-file` it is a
 * stub — the object is there, `clear` is `undefined` — and it SHADOWS the one
 * jsdom installs. Every store that persists to localStorage then dies with
 * `TypeError: localStorage.clear is not a function`: ninety-nine tests across
 * bookmarks, favorites, langChoice and the rest, all at once.
 *
 * The damage is not the failure, it is what the failure looks like. A wall of
 * red in files nobody touched, identical on a clean checkout of `main`, reads
 * as "these tests are just broken here" and gets stepped over — which is what
 * happened, and it means a real regression in any of those files would have
 * been invisible behind the noise. CI stays green throughout, because it runs
 * the pinned Node, so nothing ever contradicts the wrong conclusion.
 *
 * So: one message, before the assertions, naming the cause and the fix. The
 * version this repo runs on is `frontend/.nvmrc`, which CI's `node-version-file`
 * reads too, so there is one number rather than two that drift.
 */

// Only where a DOM is expected. `setupFiles` runs for EVERY test file, and a
// few opt out with `// @vitest-environment node` — pure-logic tests over tables
// and stylesheets, which have no window and rightly no localStorage. Checking
// unconditionally fails those for the very reason this guard exists to rule out.
const inDom =
	typeof globalThis.window !== 'undefined' && typeof globalThis.document !== 'undefined';
const storage = globalThis.localStorage as Storage | undefined;

if (inDom && typeof storage?.clear !== 'function') {
	throw new Error(
		'The test environment has no working localStorage, so every store test ' +
			'would fail for a reason that has nothing to do with the code.\n\n' +
			`Running Node ${process.version}. Node 25+ defines a global localStorage ` +
			"that shadows jsdom's and is inert without --localstorage-file.\n\n" +
			'Fix: use the Node this repo pins (frontend/.nvmrc) — `nvm use` or ' +
			'`fnm use` in frontend/, then re-run.'
	);
}
