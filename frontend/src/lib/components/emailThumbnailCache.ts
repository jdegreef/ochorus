/** Rendered email thumbnails for this page session, keyed by what was
 *  rendered — reopening the template gallery doesn't render them again. */
export const thumbnailCache = new Map<string, string>();
