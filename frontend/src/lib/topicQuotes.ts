/**
 * The bridge between the two theme vocabularies: the book-and-sermon shelves
 * (/topics/<slug>/, `library/topic_seed.py`) and the quote themes
 * (/quotes/topics/<slug>/, `library/quote_seed.py` QUOTE_TOPICS). They are
 * kept apart on purpose (a quote theme is finer than a shelf), so nothing in
 * the data joins them; this curated map does, so a reader on "Prayer" books
 * finds the prayer quotations and back, and neither page is a dead end.
 *
 * Each shelf names the quote themes it reads as, best first. A theme links back
 * to every shelf that names it. Quotes are English only, so the links are too.
 */
export const TOPIC_QUOTE_THEMES: Readonly<Record<string, readonly string[]>> = {
	prayer: ['prayer'],
	'holy-spirit': ['holy-spirit'],
	'deeper-life': ['surrender', 'holiness'],
	'grace-and-comfort': ['suffering', 'hope', 'peace'],
	'faith-and-guidance': ['faith', 'trusting-god'],
	'the-gospel-call': ['salvation', 'repentance'],
	'the-way-of-holiness': ['holiness'],
	'christ-and-the-cross': ['the-cross'],
	'abiding-in-christ': ['surrender', 'peace'],
	'the-inner-life': ['humility', 'contentment'],
	'foundations-of-the-faith': ['scripture', 'salvation'],
	'the-preached-word': ['scripture'],
	'the-grace-of-god': ['grace', 'love-of-god'],
	'victory-over-sin': ['sin-and-temptation', 'holiness'],
	'faith-for-the-impossible': ['faith', 'trusting-god']
};

/** The quote themes a shelf links, restricted to those that have a page. */
export const quoteThemesFor = <T extends { slug: string }>(topic: string, themes: T[]): T[] => {
	const bySlug = new Map(themes.map((q) => [q.slug, q]));
	return (TOPIC_QUOTE_THEMES[topic] ?? []).flatMap((s) => bySlug.get(s) ?? []);
};

/** The shelves that link a quote theme, restricted to those that have a page,
 *  in the shelves' own order. */
export const topicsForTheme = <T extends { slug: string }>(theme: string, topics: T[]): T[] =>
	topics.filter((tp) => TOPIC_QUOTE_THEMES[tp.slug]?.includes(theme));
