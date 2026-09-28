/**
 * Put a returning reader at their paragraph BEFORE first paint.
 *
 * The chapter is prerendered, so its text paints as soon as the HTML arrives,
 * at the top. The reader's own restore (`restoreScroll` in the chapter route)
 * only runs after the app's scripts have loaded and hydrated. On a cold phone
 * load that measured ~2.5s (text at 2.2s, the jump at 4.8s): long enough to
 * start reading the opening and then be yanked away.
 *
 * This runs INLINE, straight after the chapter body is parsed: it reads the
 * same saved spot the reader does — this device's anchor for the chapter, else
 * the book's synced record when it names this chapter — and scrolls there.
 * The hydrated restore still runs and corrects for font reflow; it lands where
 * this already is, so there is nothing to see.
 *
 * It stands aside, doing nothing, wherever the app decides the landing
 * instead: page mode (it pages rather than scrolls), a deliberate jump
 * (`?p=`, `?pg=`, a `#fragment`), a URL that isn't a chapter, or storage it
 * can't read. Doing nothing is always safe — the hydrated restore follows.
 *
 * FIXED TEXT, hashed into the CSP: `script-src` has no 'unsafe-inline', so the
 * policy admits this script by its SHA-256 (csp.config.js), and csp.test.ts
 * fails the build if the text below changes without the pin. The storage keys
 * are literals for the same reason (they must match `reading-schema.ts` and
 * `readerPrefs`; earlyResume.test.ts checks that they do). 64 is
 * `HEADER_OFFSET`.
 */
export const EARLY_RESUME_JS =
	"(function(){try{var b=document.currentScript&&document.currentScript.previousElementSibling;" +
	"if(!b||/[?&](p|pg)=/.test(location.search)||location.hash)return;" +
	"var m=location.pathname.match(/\\/books\\/([^/]+)\\/(\\d+)\\/?$/);if(!m)return;" +
	"var g=function(k){return JSON.parse(localStorage.getItem(k)||'{}')};" +
	"if(g('ochorus:reader-prefs').paged)return;" +
	"var a=g('ochorus:anchors')[m[1]+':'+m[2]];" +
	"if(a==null){var r=g('ochorus:progress')[m[1]];if(r&&r.order==m[2])a=r.paragraph_index}" +
	"var el=a>0&&b.children[a];if(!el)return;" +
	"el.scrollIntoView({block:'start'});scrollBy(0,-64)}catch(e){}})();";

/** The tag the chapter route renders right after its `.reading` body. */
export const EARLY_RESUME_TAG = `<script>${EARLY_RESUME_JS}</script>`;
