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
 * the book's synced record when it names this chapter, each only in the page's
 * language — and scrolls there.
 * The hydrated restore still runs and corrects for font reflow; it lands where
 * this already is, so there is nothing to see.
 *
 * It stands aside, doing nothing, wherever the app decides the landing
 * instead: page mode (stored, or the wide-screen default — it pages rather
 * than scrolls), a deliberate jump (`?p=`, `?pg=`, a `#fragment`), a URL that
 * isn't a chapter, a paragraph too near the end to reach the top before the
 * rest of the page has parsed, or storage it can't read. Doing nothing is always safe — the hydrated restore follows.
 *
 * FIXED TEXT, hashed into the CSP: `script-src` has no 'unsafe-inline', so the
 * policy admits this script by its SHA-256 (csp.config.js). It is built from
 * the reader's own storage keys and header offset, so renaming one changes the
 * text — and csp.test.ts then fails until the pin is updated, rather than the
 * script silently reading a key nobody writes. The anchor key is
 * `chapterKey(slug, order)`'s `slug:order` (earlyResume.test.ts checks it).
 */
import { ANCHOR_KEY, PROGRESS_KEY } from './reading-schema';
import { HEADER_OFFSET } from './reading';
import { READER_PREFS_KEY, WIDE_SCREEN_MIN } from './readerPrefs.svelte';

export const EARLY_RESUME_JS =
	'(function(){try{var b=document.currentScript&&document.currentScript.previousElementSibling;' +
	'if(!b||/[?&](p|pg)=/.test(location.search)||location.hash)return;' +
	'var m=location.pathname.match(/\\/books\\/([^/]+)\\/(?:modern\\/)?(\\d+)\\/?$/);if(!m)return;' +
	"var g=function(k){return JSON.parse(localStorage.getItem(k)||'{}')};" +
	// Page mode: stored, or the wide-screen default a reader who never chose gets.
	`var pm=g('${READER_PREFS_KEY}').paged;if(pm===true||(pm!==false&&innerWidth>=${WIDE_SCREEN_MIN}))return;` +
	// In THIS language only (progress.ts): an anchor is `{p, lang}` (a bare
	// number is a legacy one that restores anywhere), and the synced record
	// must be in the page's language. `<html lang>` is the locale getLang() reads.
	'var L=document.documentElement.lang;' +
	`var v=g('${ANCHOR_KEY}')[m[1]+':'+m[2]];var a=v&&typeof v=='object'?(v.lang===L?v.p:null):v;` +
	`if(a==null){var r=g('${PROGRESS_KEY}')[m[1]];if(r&&r.order==m[2]&&r.language===L)a=r.paragraph_index}` +
	'var el=a>0&&b.children[a];if(!el)return;' +
	// Mid-parse the document ends at the body, so a paragraph in the chapter's
	// last screenful can't reach the top yet; a clamped scroll would paint short
	// and then jump. Stand aside there — the hydrated restore places it.
	`var y=el.getBoundingClientRect().top+scrollY-${HEADER_OFFSET};` +
	'if(y>document.documentElement.scrollHeight-innerHeight)return;' +
	'scrollTo(0,y)}catch(e){}})();';

export const EARLY_RESUME_TAG = `<script>${EARLY_RESUME_JS}</script>`;
