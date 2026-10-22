/**
 * Which of `static/` the native app leaves out of its bundle and loads from the
 * website instead (MOBILE.md, "How the app loads images"). Plain data, read by
 * both halves of that promise so they cannot disagree:
 *
 *   * scripts/build-app.mjs deletes these folders from build-app/;
 *   * `assetUrl` ($lib/assetUrl) points every path under them at the site's
 *     origin in the app, so nothing asks the phone for a file that isn't there.
 *
 * A folder dropped here but not rewritten would be a broken image; one
 * rewritten but not dropped would be wasted megabytes — hence one list.
 * Everything else under static/ (icons, marks, emblems, textures — a few
 * hundred KB the shell paints before any network) stays in the bundle.
 */

/** Top-level folders under static/ that the app fetches from the website. */
export const REMOTE_DIRS = [
	'covers', // book covers, art grounds, og twins (~190 MB)
	'portraits', // author photos
	'illustrations', // in-chapter pictures
	'about', // the About page's photographs
	'og', // share cards: only link previews read them, never the app
	'pdfs' // book downloads: opened from the site
];

/**
 * Files under a remote folder that the app still bundles, because the reader
 * `fetch`es them rather than painting them in an `<img>`: a cross-origin
 * fetch from the app's origin would need CORS headers the static site does
 * not send, while an image needs none.
 */
export const KEEP_LOCAL = ['covers/art/credits.json'];
