/**
 * Where a downloaded book's pieces live on the phone, as paths relative to the
 * app's `offline/` folder (native.ts resolves that folder). Pure, so the rule
 * is testable without a device, and shared by both sides that need it: the
 * writer (native.ts) and the reader of image URLs ($lib/appOffline).
 *
 * Only RELATIVE paths are ever recorded. The folder's absolute location is
 * asked for at each launch (`offlineFileBase`): on iOS the app's container
 * path changes across updates and reinstalls, so a stored `file://` URI would
 * point at nothing after the next update.
 */

/** An API response (`/api/library/books/humility/?language=en`): one flat
 *  file, the key encoded whole — reversibly (`decodeURIComponent`), with no
 *  `/`, `?` or `=` left to mean anything to the filesystem. Read back through
 *  the Filesystem plugin only, never by URL, so the `%`s are just bytes. */
export const apiFile = (key: string): string => `api/${encodeURIComponent(key)}.json`;

/** A site image (`/covers/humility-320.webp`): the same path under `img/`,
 *  extension kept — the app's web view serves the file by URL, and takes its
 *  type from that extension. Null for anything that is not a plain
 *  root-relative path (`..`, an empty or encoded segment, a query), which is
 *  then simply not saved. */
export function imageFile(path: string): string | null {
	const [lead, ...segments] = path.split('/');
	if (lead !== '' || !segments.length) return null;
	if (segments.some((s) => !s || s === '.' || s === '..' || /[%?#\\]/.test(s))) return null;
	return `img${path}`;
}

/** The URL the web view loads a saved file from: `base` (the folder's URL,
 *  from `offlineFileBase`) plus the file's path, each segment URL-encoded. */
export const offlineFileUrl = (base: string, file: string): string =>
	`${base.replace(/\/+$/, '')}/${file.split('/').map(encodeURIComponent).join('/')}`;
