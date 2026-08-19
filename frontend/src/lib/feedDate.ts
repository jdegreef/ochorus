/**
 * Date formatting for the Atom feed, tolerant of a missing or unparseable value.
 *
 * Lives here rather than inline in `feed.xml/+server.ts` so it can be tested:
 * the bug it guards fails the PRERENDER, which fails the whole static build, so
 * "the feed is fine" is not something to find out at deploy time.
 *
 * The feed deliberately KEEPS undated rows — a backend deploy can briefly serve
 * works whose `created_at` hasn't landed yet, and dropping them would make the
 * feed flicker. But `new Date(undefined).toISOString()` throws a RangeError on
 * the resulting Invalid Date, so rendering those rows crashed the build: a
 * cosmetic data gap turned into a deploy outage, which is the exact race the
 * feed says it is built to survive.
 */

/**
 * Epoch, used for anything undated. A deliberate choice over "now": it sorts and
 * reads as the oldest thing in the library, so a row with a missing date can
 * never masquerade as the newest entry in a reader's feed.
 */
export const FEED_EPOCH = '1970-01-01T00:00:00.000Z';

/** An ISO timestamp, or FEED_EPOCH when the input is absent or unparseable. */
export function isoOrEpoch(date: string | null | undefined): string {
	const parsed = new Date(date ?? '');
	return Number.isNaN(parsed.getTime()) ? FEED_EPOCH : parsed.toISOString();
}
