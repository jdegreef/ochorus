/**
 * "Listen to the whole book" — the book page's way into read-aloud for a book
 * of the Bible: open its first chapter already listening, and let the reader's
 * audiobook roll-over (`onListenFinish` in the chapter reader) carry it on
 * chapter by chapter to the end, as it does for any book.
 *
 * The intent crosses the navigation as a one-shot in memory, not a URL
 * parameter: a `?listen` link would start speaking again on a reload, or for
 * whoever it was shared with — where, with no tap on the page, the browser
 * refuses to speak anyway. Held for ONE chapter arrival: the first chapter the
 * reader opens consumes it, matching or not, so a link opened in a new tab
 * (whose click never navigated this one) can't make a later visit surprise-play.
 */
import { BIBLE_SERIES } from '$lib/bible';

/** Whether the book page offers "Listen to the whole book": a book of the Bible. */
export const listenBookFor = (book: { series?: { slug: string } | null }) =>
	book.series?.slug === BIBLE_SERIES;

let pending: string | null = null;

/** The book page asks for `slug`'s chapter `order` to open listening. */
export function requestBookListen(slug: string, order: number): void {
	pending = `${slug}:${order}`;
}

/** The reader, on arriving at a chapter: was it asked to start listening here?
 *  Consumes the request either way. */
export function takeBookListen(slug: string, order: number): boolean {
	const hit = pending === `${slug}:${order}`;
	pending = null;
	return hit;
}
