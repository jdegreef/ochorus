/**
 * In-book illustrations: the `<img>`s a chapter body may carry.
 *
 * The backend sanitizer (`library/sanitize.py`, `ILLUSTRATION_SRC`) admits an
 * image only from our own `/illustrations/<work>/<name>.<ext>`, so every src
 * that reaches the reader has this shape — which is what lets a plain pattern,
 * not a DOM parse, find them. The DOM would also fetch them, which is the one
 * thing a caller listing them (to cache for offline) must not trigger twice.
 */

const IMG_SRC = /<img\b[^>]*?\ssrc="(\/illustrations\/[^"]+)"/gi;

/** The distinct illustration paths a chapter's body shows, in order. */
export function illustrationSrcs(bodyHtml: string): string[] {
	return [...new Set([...bodyHtml.matchAll(IMG_SRC)].map((m) => m[1]))];
}
