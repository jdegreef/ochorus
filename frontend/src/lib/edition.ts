/**
 * A young-reader edition is a separate same-language book whose slug ends in
 * `-teens` / `-children` and whose title carries a localized "(For Teens)" /
 * "(For Children)" suffix (the reader-facing half of the convention the backend
 * keys on — `serializers.EDITION_SUFFIXES`). On a narrow card the title's
 * `line-clamp-2` can eat that suffix, so "Talks to the Farmer (For Teens)" and
 * "… (For Children)" render identically and look like duplicates.
 *
 * `splitEdition` pulls the audience out of the title so a card can show it on
 * its own, unclamped, line. It reads the audience from the TITLE itself — which
 * is already translated per book — so no new UI strings are needed in any
 * locale.
 *
 * It is deliberately conservative: it returns a split only when BOTH signals
 * agree — the slug suffix AND a trailing parenthetical in the title. That keeps
 * a real work whose own title happens to end that way from being mis-split:
 * `divine-songs-for-children` ("Divine Songs for Children") has the slug suffix
 * but no trailing "(…)", so it falls through to its full title unchanged.
 */
const EDITION_SLUG = /-(?:teens|children)$/;
const TRAILING_PAREN = /^(.*\S)\s*\(([^()]+)\)$/;

export function splitEdition(
	slug: string,
	title: string
): { base: string; audience: string } | null {
	if (!EDITION_SLUG.test(slug)) return null;
	const m = title.trim().match(TRAILING_PAREN);
	if (!m) return null;
	return { base: m[1], audience: m[2].trim() };
}
