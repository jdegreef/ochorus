/**
 * "The Story of the Bible" (/bible/story/): the whole Bible walked in story
 * order, creation to new creation, one short section per era, each linking the
 * Bible books that tell it and a key chapter or two.
 *
 * The prose is English, like the hub's own copy (`BIBLE_STARTS` in
 * $lib/bible): the page exists only where the Bible does (BIBLE_LOCALES,
 * English today), and it is imported by that route alone, so it loads with
 * the page instead of riding in every locale's catalogue. Its headings and
 * link labels are chrome and go through the catalogue.
 *
 * It quotes no Scripture on purpose: a quotation here would have to be the
 * Open Word Bible's own wording (CLAUDE.md, "Sourcing"), and the links carry
 * the reader to the text itself.
 *
 * The key chapters are given in the Bible's own numbers; `storyKeys` turns
 * them into reader chapters (`bibleChapterOrder`: each book opens on an
 * introduction). Most are the 60-day plan's own (`the-story-of-the-bible` in
 * `library/plan_seed.py`), so the page and the plan read the same story.
 */

import { CANON } from '$lib/sermonCanon';
import { bibleChapterOrder, chapterLabel } from '$lib/bible';
import { bookChapterPath } from '$lib/reading-schema';

export { BIBLE_STORY_PATH } from '$lib/bible';

/** The 60-day reading plan that reads the same story, a chapter a day. */
export const STORY_PLAN_SLUG = 'the-story-of-the-bible';
/** The house book that tells the whole story for teens (an Ochorus Original). */
export const STORY_BOOK = { slug: 'the-big-story', title: 'The Big Story' } as const;

/** The page's one-sentence description: its tagline and its meta description. */
export const STORY_TAGLINE =
	'The whole Bible as one story, from creation to new creation, and the books that tell each part of it.';

/**
 * The `the-bible` series' book slugs in canonical order: index + 1 is the
 * book's `series_position` (1 Genesis … 66 Revelation), the numbering `CANON`
 * and `chapterLabel` use. Checked against the committed fixtures by the test.
 */
export const BIBLE_SLUGS: readonly string[] = [
	'genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy',
	'joshua', 'judges', 'ruth', '1-samuel', '2-samuel', '1-kings', '2-kings',
	'1-chronicles', '2-chronicles', 'ezra', 'nehemiah', 'esther',
	'job', 'psalms', 'proverbs', 'ecclesiastes', 'song-of-songs',
	'isaiah', 'jeremiah', 'lamentations', 'ezekiel', 'daniel',
	'hosea', 'joel', 'amos', 'obadiah', 'jonah', 'micah', 'nahum', 'habakkuk',
	'zephaniah', 'haggai', 'zechariah', 'malachi',
	'gospel-of-matthew', 'gospel-of-mark', 'gospel-of-luke', 'gospel-of-john',
	'acts-of-the-apostles',
	'romans', '1-corinthians', '2-corinthians', 'galatians', 'ephesians', 'philippians',
	'colossians', '1-thessalonians', '2-thessalonians', '1-timothy', '2-timothy', 'titus',
	'philemon',
	'hebrews', 'james', '1-peter', '2-peter', '1-john', '2-john', '3-john', 'jude',
	'revelation'
];

/** A book's place in the canon (1–66), or null if it is not a Bible book. */
export const canonPosition = (slug: string): number | null => {
	const i = BIBLE_SLUGS.indexOf(slug);
	return i === -1 ? null : i + 1;
};

/** A key chapter: a book and the Bible's own chapter number in it. */
export interface StoryKey {
	slug: string;
	chapter: number;
}

export interface StorySection {
	id: string;
	/** The era's heading. */
	title: string;
	/** Where the Bible tells it ("Genesis 12–50"), or how long it lasts. */
	period: string;
	/** Two or three sentences: plain, accurate, no quotation. */
	prose: string;
	/** The books that tell it, slugs in canonical order. */
	books: readonly string[];
	/** One or two key chapters. */
	keys: readonly StoryKey[];
	testament: 'old' | 'new';
	/**
	 * A bridge between the testaments, told in a line, with no book of its
	 * own (the silent years). Drawn as a pause on the timeline, not an era.
	 */
	interlude?: boolean;
}

export const BIBLE_STORY: readonly StorySection[] = [
	{
		id: 'creation',
		title: 'Creation',
		period: 'Genesis 1–2',
		prose:
			'The Bible opens with God and nothing else. He makes the world by his word, calls it good, and makes man and woman in his own image to care for it. They live in a garden with God, in a world as it was meant to be.',
		books: ['genesis'],
		keys: [
			{ slug: 'genesis', chapter: 1 },
			{ slug: 'genesis', chapter: 2 }
		],
		testament: 'old'
	},
	{
		id: 'fall',
		title: 'The fall',
		period: 'Genesis 3–11',
		prose:
			'Adam and Eve choose their own way over God’s, and everything changes: shame, pain and death come into the world, and they are sent out of the garden. Even then God speaks a promise of rescue. The chapters that follow show how far the damage spreads, through Cain, the flood and the tower of Babel.',
		books: ['genesis'],
		keys: [
			{ slug: 'genesis', chapter: 3 },
			{ slug: 'genesis', chapter: 11 }
		],
		testament: 'old'
	},
	{
		id: 'patriarchs',
		title: 'Abraham and his family',
		period: 'Genesis 12–50',
		prose:
			'God calls Abraham to leave his home and promises to make of him a great nation, through which all the families of the earth will be blessed. The promise passes, through many failures, to Isaac, Jacob and Jacob’s twelve sons. Genesis ends with the family in Egypt, where Joseph, sold as a slave by his brothers, has risen to save them from famine.',
		books: ['genesis'],
		keys: [
			{ slug: 'genesis', chapter: 12 },
			{ slug: 'genesis', chapter: 50 }
		],
		testament: 'old'
	},
	{
		id: 'exodus',
		title: 'Out of Egypt',
		period: 'Exodus 1–18',
		prose:
			'Generations later Jacob’s descendants, the Israelites, are slaves in Egypt. God hears their cry and sends Moses to bring them out. At the Passover and the crossing of the sea he rescues his people, and the exodus becomes the great picture of salvation for the rest of the Bible.',
		books: ['exodus'],
		keys: [
			{ slug: 'exodus', chapter: 3 },
			{ slug: 'exodus', chapter: 14 }
		],
		testament: 'old'
	},
	{
		id: 'law',
		title: 'The law and the wilderness',
		period: 'Exodus 19 – Deuteronomy',
		prose:
			'At Mount Sinai God makes a covenant with Israel, gives them his law, and comes to live among them in the tabernacle, with sacrifices to deal with their sin. When they refuse to enter the promised land, they wander forty years in the wilderness. On its border Moses sets the law before a new generation and urges them to love God with all their heart.',
		books: ['exodus', 'leviticus', 'numbers', 'deuteronomy'],
		keys: [
			{ slug: 'exodus', chapter: 20 },
			{ slug: 'deuteronomy', chapter: 6 }
		],
		testament: 'old'
	},
	{
		id: 'conquest',
		title: 'The land and the judges',
		period: 'Joshua – Ruth',
		prose:
			'Under Joshua, Israel crosses the Jordan and settles in the land God promised. Then comes a long, repeating cycle: the people turn away, trouble comes, they cry out, and God raises up a judge to deliver them. In the middle of those dark days the book of Ruth tells a quiet story of faithfulness, and of a family line that leads to King David.',
		books: ['joshua', 'judges', 'ruth'],
		keys: [
			{ slug: 'joshua', chapter: 1 },
			{ slug: 'judges', chapter: 2 }
		],
		testament: 'old'
	},
	{
		id: 'kings',
		title: 'The kings',
		period: '1 Samuel – 2 Chronicles',
		prose:
			'Israel asks for a king. After Saul comes David, the shepherd boy, to whom God promises a son whose kingdom will never end; Solomon, his son, builds the temple in Jerusalem, but after him the kingdom splits in two, Israel in the north and Judah in the south, and most of their kings lead the people away from God. Beside the story stand Israel’s books of song and wisdom: the Psalms, many of them David’s; Proverbs, Ecclesiastes and the Song of Songs, linked with Solomon; and Job.',
		books: [
			'1-samuel',
			'2-samuel',
			'1-kings',
			'2-kings',
			'1-chronicles',
			'2-chronicles',
			'job',
			'psalms',
			'proverbs',
			'ecclesiastes',
			'song-of-songs'
		],
		keys: [
			{ slug: '2-samuel', chapter: 7 },
			{ slug: '1-kings', chapter: 12 }
		],
		testament: 'old'
	},
	{
		id: 'prophets',
		title: 'The prophets',
		period: 'Isaiah – Zephaniah',
		prose:
			'Through the years of the kings, God sends prophets to call his people back to him, away from idols and injustice, before judgement falls. Most of their warnings go unheeded. Yet their books are full of hope as well: of a King to come from David’s line, and of a servant who will suffer for the sins of many.',
		books: [
			'isaiah',
			'hosea',
			'joel',
			'amos',
			'jonah',
			'micah',
			'nahum',
			'habakkuk',
			'zephaniah'
		],
		keys: [
			{ slug: 'isaiah', chapter: 53 },
			{ slug: 'hosea', chapter: 11 }
		],
		testament: 'old'
	},
	{
		id: 'exile',
		title: 'Exile',
		period: '2 Kings 17–25 · Jeremiah – Daniel',
		prose:
			'Assyria takes the northern kingdom, and later Babylon destroys Jerusalem and its temple and carries Judah away. Lamentations mourns the city; in Babylon, Ezekiel and Daniel speak of a God who has not abandoned his people. Jeremiah, who saw the end coming, also speaks of a new covenant, written on the heart.',
		books: ['2-kings', 'jeremiah', 'lamentations', 'ezekiel', 'daniel', 'obadiah'],
		keys: [
			{ slug: '2-kings', chapter: 25 },
			{ slug: 'ezekiel', chapter: 37 }
		],
		testament: 'old'
	},
	{
		id: 'return',
		title: 'The return',
		period: 'Ezra – Esther · Haggai – Malachi',
		prose:
			'When Persia conquers Babylon, the exiles are allowed to go home. They rebuild the temple and, under Nehemiah, the walls of Jerusalem, and Ezra reads them the law again; the book of Esther shows God keeping his people who stayed in Persia. The last prophets urge them on, and the Old Testament closes still waiting for the promised King.',
		books: ['ezra', 'nehemiah', 'esther', 'haggai', 'zechariah', 'malachi'],
		keys: [
			{ slug: 'ezra', chapter: 1 },
			{ slug: 'nehemiah', chapter: 8 }
		],
		testament: 'old'
	},
	{
		id: 'silent-years',
		title: 'The silent years',
		period: 'About four hundred years',
		prose:
			'Between Malachi and the coming of Jesus lie some four hundred years the Old Testament does not tell: empires rise and fall, and Israel waits.',
		books: [],
		keys: [],
		testament: 'old',
		interlude: true
	},
	{
		id: 'jesus',
		title: 'Jesus',
		period: 'The Gospels',
		prose:
			'In Bethlehem, Jesus is born to Mary, the long-promised son of David and the Son of God. He announces that the kingdom of God has come near, teaches, heals the sick, forgives sinners and calls twelve disciples to follow him. Four Gospels tell his life, each in its own way.',
		books: ['gospel-of-matthew', 'gospel-of-mark', 'gospel-of-luke', 'gospel-of-john'],
		keys: [
			{ slug: 'gospel-of-luke', chapter: 2 },
			{ slug: 'gospel-of-matthew', chapter: 5 }
		],
		testament: 'new'
	},
	{
		id: 'cross',
		title: 'The cross and the empty tomb',
		period: 'The Gospels',
		prose:
			'Jesus goes up to Jerusalem knowing what waits for him there. He shares a last supper with his disciples, is arrested, and is crucified, giving his life for the sins of the world. On the third day the tomb is empty: he is risen, and he appears to his friends.',
		books: ['gospel-of-matthew', 'gospel-of-mark', 'gospel-of-luke', 'gospel-of-john'],
		keys: [
			{ slug: 'gospel-of-mark', chapter: 15 },
			{ slug: 'gospel-of-john', chapter: 20 }
		],
		testament: 'new'
	},
	{
		id: 'church',
		title: 'The church',
		period: 'Acts',
		prose:
			'Jesus returns to his Father and sends the Holy Spirit on his followers at Pentecost. From Jerusalem the good news spreads outward, carried by Peter, by Paul, once its fierce opponent, and by many others, until there are churches across the Roman world. Acts ends with Paul in Rome, still preaching.',
		books: ['acts-of-the-apostles'],
		keys: [
			{ slug: 'acts-of-the-apostles', chapter: 2 },
			{ slug: 'acts-of-the-apostles', chapter: 9 }
		],
		testament: 'new'
	},
	{
		id: 'letters',
		title: 'The letters',
		period: 'Romans – Jude',
		prose:
			'Paul and other leaders of the first Christians write to the young churches and to friends, explaining what Jesus has done and how to live in the light of it. The letters speak of grace and faith, of Jew and Gentile made one people, of love, suffering and hope. They are written to real congregations with real troubles, and they still speak to ours.',
		books: [
			'romans',
			'1-corinthians',
			'2-corinthians',
			'galatians',
			'ephesians',
			'philippians',
			'colossians',
			'1-thessalonians',
			'2-thessalonians',
			'1-timothy',
			'2-timothy',
			'titus',
			'philemon',
			'hebrews',
			'james',
			'1-peter',
			'2-peter',
			'1-john',
			'2-john',
			'3-john',
			'jude'
		],
		keys: [
			{ slug: 'romans', chapter: 8 },
			{ slug: 'ephesians', chapter: 2 }
		],
		testament: 'new'
	},
	{
		id: 'new-creation',
		title: 'The new creation',
		period: 'Revelation',
		prose:
			'The Bible ends where it began, with God and his world. In visions given to John, Jesus reigns, evil is finally overthrown, and heaven and earth are made new. God lives with his people, and there is no more death, mourning or pain.',
		books: ['revelation'],
		keys: [
			{ slug: 'revelation', chapter: 21 },
			{ slug: 'revelation', chapter: 22 }
		],
		testament: 'new'
	}
];

/** A link the page draws: its label and its unlocalized href. */
export interface StoryLink {
	label: string;
	href: string;
}

/** A section's books as links to their book pages, named as the canon strip names them. */
export const storyBooks = (section: StorySection): StoryLink[] =>
	section.books.map((slug) => ({
		label: CANON[canonPosition(slug)! - 1][0],
		href: `/books/${slug}`
	}));

/** A section's key chapters as links into the reader ("Psalm 23", "Romans 8"). */
export const storyKeys = (section: StorySection): StoryLink[] =>
	section.keys.map(({ slug, chapter }) => ({
		label: chapterLabel(canonPosition(slug), chapter) ?? `${slug} ${chapter}`,
		href: bookChapterPath(slug, bibleChapterOrder(chapter), false)
	}));

/** The eras the timeline numbers (the interlude is a pause, not an era). */
export const storyEras = (sections: readonly StorySection[] = BIBLE_STORY) =>
	sections.filter((s) => !s.interlude);
