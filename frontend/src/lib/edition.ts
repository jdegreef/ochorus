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
const EDITION_SLUG = /-(teens|children)$/;

/** The young-reader edition a slug names by the convention, or null for a
 *  full text. The slug alone — see `splitEdition` for when that isn't enough. */
export function editionKind(slug: string): 'teens' | 'children' | null {
	return (slug.match(EDITION_SLUG)?.[1] as 'teens' | 'children' | undefined) ?? null;
}
const TRAILING_PAREN = /^(.*\S)\s*\(([^()]+)\)$/;

export function splitEdition(
	slug: string,
	title: string
): { base: string; audience: string; kind: 'teens' | 'children' } | null {
	const edition = slug.match(EDITION_SLUG);
	if (!edition) return null;
	const m = title.trim().match(TRAILING_PAREN);
	if (!m) return null;
	return { base: m[1], audience: m[2].trim(), kind: edition[1] as 'teens' | 'children' };
}

/**
 * Whether the chapter reader treats a chapter as a children's one: its young
 * layout, story styling, Listen button, gentle speed and spoken questions. A
 * "-children" edition is one; so is a book in a series written for young
 * readers (Tell Me the Story, Brave for God, Rooted), which has no edition to
 * say so. A teens edition never is, whatever its series.
 */
export function childrensReading(
	kind: 'teens' | 'children' | null,
	bookAudience: string | undefined
): boolean {
	return kind === 'children' || (kind === null && bookAudience === 'young_readers');
}

/**
 * The full text a young-reader edition retells — `<base>` for
 * `<base>-teens` / `<base>-children` — or null for anything else. Both signals
 * must agree, as for `splitEdition`: the slug suffix AND a trailing
 * "(For …)" in the title, so a real work whose slug merely ends that way
 * ("Come Ye Children") is never taken for a retelling. A base that is itself
 * an edition slug (`x-teens-children`) is no full text either. The link
 * `serializers.sibling_editions` derives; `authorIndex.foldEditions` and the
 * shelf's fold below both read it here.
 */
export function editionBase(book: { slug: string; title: string }): string | null {
	if (!splitEdition(book.slug, book.title)) return null;
	const base = book.slug.replace(EDITION_SLUG, '');
	return EDITION_SLUG.test(base) ? null : base;
}

/**
 * How many editions each work has on this shelf — the full text plus its
 * young-reader editions in the same language, keyed by the full text's slug.
 * Only works with more than one edition appear: a young-reader edition whose
 * full text is not on the shelf (a language with only the retelling) is a
 * work of its own.
 */
export function editionFamilies(books: readonly { slug: string; title: string }[]): Map<string, number> {
	const slugs = new Set(books.map((b) => b.slug));
	const sizes = new Map<string, number>();
	for (const b of books) {
		const base = editionBase(b);
		if (base && slugs.has(base)) sizes.set(base, (sizes.get(base) ?? 1) + 1);
	}
	return sizes;
}

/**
 * One slot per work (design review #26): a young-reader edition drops out of
 * `list` when its full text is in `list` too — the full edition's card stands
 * for the family, and its book page is where the reader chooses. Collapsing
 * within the list, not against the whole shelf, is what keeps a search honest:
 * a query or filter that matches the teens edition and not the full text still
 * shows the teens edition, as itself. Order is kept.
 */
export function collapseEditions<T extends { slug: string; title: string }>(list: readonly T[]): T[] {
	const slugs = new Set(list.map((b) => b.slug));
	return list.filter((b) => {
		const base = editionBase(b);
		return !(base && slugs.has(base));
	});
}
