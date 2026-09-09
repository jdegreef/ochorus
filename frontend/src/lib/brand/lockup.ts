import lockup from './ochorus-lockup.svg?raw';

/**
 * The Ochorus wordmark as a reusable SVG `<symbol>`, so the ~4.3 KB of path is
 * defined ONCE per document and every BrandMark is a tiny `<use>` reference.
 *
 * BrandMark previously inlined the whole file (`{@html lockup}`) on every
 * instance, and the book shelf renders one per cover — 85 copies, ~365 KB of
 * duplicated path, made /books a 630 KB page. `<symbol>` + `<use>` keeps the
 * mark inline (so `fill="currentColor"` still resolves per theme, which an
 * `<img>` cannot) while paying for the geometry only once.
 *
 * Built from the committed asset at build time, so the source of truth stays the
 * SVG file `brandAssets.test.ts` guards — never a hand-copied path.
 */
export const LOCKUP_SYMBOL_ID = 'ochorus-lockup';

/** The wordmark's viewBox, for the `<svg>` wrapper that `<use>`s the symbol. */
export const LOCKUP_VIEWBOX = /viewBox="([^"]+)"/.exec(lockup)?.[1] ?? '0 0 1020.6 616.3';

const inner = lockup
	.replace(/<!--[\s\S]*?-->/g, '') // the generated-by comment
	.replace(/<svg\b[^>]*>/, '') // the opening <svg …>
	.replace(/<\/svg>\s*$/, '') // and its close
	.trim();

/** The `<symbol>` markup, injected once by BrandSprite. `fill="currentColor"`
 *  so each `<use>` takes the surrounding text colour. */
export const LOCKUP_SYMBOL = `<symbol id="${LOCKUP_SYMBOL_ID}" viewBox="${LOCKUP_VIEWBOX}" fill="currentColor">${inner}</symbol>`;
