/**
 * Length buckets for the sermons shelf's length filter.
 *
 * A sermon is "short" (under 10 min), "mid" (10–30 min inclusive), or "long"
 * (over 30 min), measured by the SAME whole-minute reading time the shelf and
 * every row already print (`readingMinutes`) — so a sermon shown as "9 min"
 * filters as short and one shown as "31 min" as long, and the buckets follow
 * the reader's own pace exactly as the printed times do. Keep the classifier
 * pure (minutes in, bucket out); the caller supplies the minutes.
 */
export type LengthBucket = 'short' | 'mid' | 'long';

/** The buckets shortest-first, for building the filter's options in order. */
export const LENGTH_BUCKETS: readonly LengthBucket[] = ['short', 'mid', 'long'];

/**
 * Which bucket a whole-minute reading time falls in. Boundaries: under 10 is
 * short, 10 through 30 (inclusive) is mid, over 30 is long.
 */
export function lengthBucket(minutes: number): LengthBucket {
	if (minutes < 10) return 'short';
	if (minutes <= 30) return 'mid';
	return 'long';
}
