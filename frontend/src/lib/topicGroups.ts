/**
 * The families the Topics hub sorts its shelves into (design review #23: "five
 * headings turn 33 cards into a map").
 *
 * Kept here, beside `TOPIC_META` in `emblemNames.ts`, rather than in the seed:
 * the grouping is how ONE page lays the shelves out, not a fact about a topic
 * the API needs. A slug listed in no group is not dropped — it lands in the
 * trailing `more` family, so a shelf seeded without an entry here still shows
 * (`topicGroups.test.ts` fails until it is placed, so that stays rare).
 *
 * Order matters twice: the families in the order they are listed, and each
 * family's shelves in the order written — an editorial order, not the seed's.
 */
export const TOPIC_GROUPS = [
	{
		id: 'innerLife',
		slugs: [
			'prayer',
			'the-inner-life',
			'deeper-life',
			'abiding-in-christ',
			'holy-spirit',
			'day-by-day',
			'soar-like-the-eagle'
		]
	},
	{
		id: 'christianLife',
		slugs: [
			'faith-and-guidance',
			'the-way-of-holiness',
			'victory-over-sin',
			'faith-for-the-impossible',
			'grace-and-comfort',
			'the-body-of-christ',
			'for-those-who-lead',
			'men-of-valour'
		]
	},
	{
		id: 'gospel',
		slugs: [
			'the-gospel-call',
			'christ-and-the-cross',
			'the-grace-of-god',
			'foundations-of-the-faith',
			'the-preached-word',
			'enduring-classics'
		]
	},
	{
		id: 'history',
		slugs: [
			'voices-of-the-early-church',
			'the-puritans',
			'the-great-awakening',
			'the-wesleys-and-early-methodism',
			'revival-and-missions',
			'to-the-ends-of-the-earth',
			'the-east-african-revival',
			'saints-of-the-african-diaspora',
			'women-of-faith',
			'contemporary-voices'
		]
	},
	{ id: 'young', slugs: ['for-young-readers', 'for-teens'] }
] as const satisfies readonly { id: string; slugs: readonly string[] }[];

/** A family's id — one of TOPIC_GROUPS', or the trailing fallback. */
export type TopicGroupId = (typeof TOPIC_GROUPS)[number]['id'] | 'more';

/** The i18n key of a family's heading (`topics_group_<id>` in the catalogues). */
export const topicGroupKey = (id: TopicGroupId): string => `topics.group.${id}`;

/**
 * Sort `topics` into families: each family's shelves in its written order, the
 * unplaced ones (in the order given) under `more`, empty families dropped — a
 * language whose shelves are all untranslated in one family shows no heading
 * for it.
 */
export function groupTopics<T extends { slug: string }>(
	topics: readonly T[]
): { id: TopicGroupId; topics: T[] }[] {
	const bySlug = new Map(topics.map((t) => [t.slug, t]));
	const placed = new Set<string>();
	const groups: { id: TopicGroupId; topics: T[] }[] = TOPIC_GROUPS.map(({ id, slugs }) => ({
		id,
		topics: (slugs as readonly string[]).flatMap((s) => {
			const t = bySlug.get(s);
			if (!t) return [];
			placed.add(s);
			return [t];
		})
	}));
	groups.push({
		id: 'more',
		topics: topics.filter((t) => !placed.has(t.slug))
	});
	return groups.filter((g) => g.topics.length > 0);
}
