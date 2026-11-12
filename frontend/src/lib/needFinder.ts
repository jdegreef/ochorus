import {
	getTopic,
	listPlans,
	toCoverFace,
	tileFace,
	type BookSummary,
	type CoverFace,
	type PlanSummary,
	type SermonSummary,
	type TopicAuthor,
	type TopicDetail
} from '$lib/library-public';
import { editionKind } from '$lib/edition';
import { authorPath, isImprint } from '$lib/originals';
import { sermonCoverFace } from '$lib/sermonArt';
import { DEFAULT_WPM } from '$lib/readingPace.svelte';
import { TONIGHT_MAX_MINUTES } from '$lib/tonightShelf';

/**
 * "What do you need today?" — a situation-first way into the topic shelves.
 *
 * Each situation is ONE existing topic (its slug in `topic_seed.py` /
 * `TOPIC_GROUPS`) and, optionally, one existing reading plan written for the
 * same need. Nothing here is content: the picks are chosen from what the topic
 * already holds in the reader's language. Change the curation here, nowhere
 * else; `needFinder.test.ts` holds every slug to a real topic and plan.
 *
 * A situation with no shelf of its own is left out rather than forced onto a
 * near one (there is no shelf on forgiveness, so there is no "I'm struggling
 * to forgive" chip).
 */
export interface Need {
	/** The chip's id: its label is `home.need.<id>` in the catalogues. */
	id: string;
	/** The topic whose shelf the picks come from, and "More on …" links to. */
	topic: string;
	/** A plan for the same need, offered as the third pick where this language has it. */
	plan?: string;
}

export const NEEDS: readonly Need[] = [
	{ id: 'anxious', topic: 'faith-and-guidance', plan: 'waiting-on-god-trust' },
	{ id: 'prayerDry', topic: 'prayer', plan: 'school-of-prayer' },
	{ id: 'grieving', topic: 'grace-and-comfort', plan: 'faith-in-the-fire' },
	{ id: 'newToFaith', topic: 'the-gospel-call', plan: 'new-to-the-faith' },
	{ id: 'failing', topic: 'victory-over-sin', plan: 'pursuit-of-holiness' },
	{ id: 'farFromGod', topic: 'abiding-in-christ' },
	{ id: 'deeper', topic: 'deeper-life', plan: 'deeper-life-in-christ' }
];

/** The i18n key of a chip's label. */
export const needLabelKey = (id: string): string => `home.need.${id}`;

/**
 * Works a topic must hold in the reader's language for its chip to show: one
 * short read, one book and one more, so three — and at least one of them a book.
 */
export const NEED_MIN_WORKS = 3;
/** Fewer qualifying chips than this and the finder does not show at all. */
export const NEED_MIN_CHIPS = 3;

/**
 * The situations this language can answer, in `NEEDS` order — from the topic
 * list's per-language counts, so it costs no request of its own. Empty when
 * fewer than `NEED_MIN_CHIPS` qualify: a row of two chips is not a finder.
 */
export function availableNeeds(
	topics: readonly { slug: string; book_count: number; sermon_count: number }[]
): string[] {
	const bySlug = new Map(topics.map((t) => [t.slug, t]));
	return shownNeeds(
		NEEDS.filter((n) => {
			const t = bySlug.get(n.topic);
			return !!t && t.book_count >= 1 && t.book_count + t.sermon_count >= NEED_MIN_WORKS;
		}).map((n) => n.id)
	).map((n) => n.id);
}

/**
 * The situations to draw for these ids, in `NEEDS` order — or none when fewer
 * than `NEED_MIN_CHIPS` are real ones. The one gate both the home page (finder
 * or topic chips?) and the finder itself read, so an id a cached snapshot
 * carries but `NEEDS` no longer has cannot leave the page with neither.
 */
export function shownNeeds(ids: readonly string[]): Need[] {
	const shown = NEEDS.filter((n) => ids.includes(n.id));
	return shown.length >= NEED_MIN_CHIPS ? shown : [];
}

/** A sermon at or under this many words is a "short read": 20 minutes at the
 *  default pace — the home page's other "short" rule (the Tonight shelf). */
export const SHORT_READ_WORDS = TONIGHT_MAX_MINUTES * DEFAULT_WPM;

export type NeedPickKind = 'shortRead' | 'book' | 'plan' | 'article' | 'life';

export interface NeedPick {
	kind: NeedPickKind;
	/** Unlocalized path; the component localizes it. */
	href: string;
	title: string;
	/** The muted line under the title: an author, a length, a chapter. */
	byline: string;
	/** For the reading-time label: words in a short read. */
	words?: number;
	/** A chapter-one short read names its chapter, not a length. */
	chapter?: number;
	/** The content language of the title (for `lang`). */
	language: string;
	cover?: CoverFace;
	/** The author pick wears a face, not a cover. */
	portrait?: TopicAuthor;
}

export interface NeedPicks {
	topic: { slug: string; title: string };
	picks: NeedPick[];
}

const isFullText = (b: BookSummary) => !editionKind(b.slug);
const wordsPerChapter = (b: BookSummary) =>
	b.word_count && b.chapter_count ? b.word_count / b.chapter_count : Infinity;

function shortSermon(sermons: SermonSummary[]): SermonSummary | undefined {
	// The shelf's own (editorial) order first: the first short one it lists.
	// None short enough → the shortest of known length; an unknown (0) length
	// only when no sermon has one.
	const known = sermons.filter((s) => s.word_count > 0);
	return (
		known.find((s) => s.word_count <= SHORT_READ_WORDS) ??
		[...known].sort((a, b) => a.word_count - b.word_count)[0] ??
		sermons[0]
	);
}

/**
 * The three picks for one situation, from its topic's detail payload and this
 * language's plans. Pure, so the choice is tested without an API:
 *
 *  1. a short read — the shelf's first short sermon, or (a shelf with no
 *     sermons here) chapter one of the book with the shortest chapters;
 *  2. a book — the shelf's lead full text (young-reader editions only when
 *     nothing else is there), never the short read's own book;
 *  3. one more — the situation's plan if this language has it, else the
 *     shelf's first article, else a life: the first author on the shelf other
 *     than the book's.
 *
 * Fewer than three only when the shelf is thinner than `availableNeeds`
 * promised (the counts and the detail disagree); the caller shows what there is.
 */
export function choosePicks(need: Need, topic: TopicDetail, plans: readonly PlanSummary[]): NeedPicks {
	const picks: NeedPick[] = [];
	const books = [...topic.books.filter(isFullText), ...topic.books.filter((b) => !isFullText(b))];

	let shortBook: BookSummary | undefined;
	const sermon = shortSermon(topic.sermons);
	if (sermon) {
		picks.push({
			kind: 'shortRead',
			href: `/sermons/${sermon.slug}`,
			title: sermon.title,
			byline: sermon.author.name,
			words: sermon.word_count,
			language: sermon.language,
			cover: sermonCoverFace(sermon)
		});
	} else if (books.length > 1) {
		// Chapter one of the book with the shortest chapters — but not the lead,
		// which is pick two. A full text over a young-reader edition: an
		// edition's short chapters would win on length alone, and an adult
		// shelf's short read should not be "(For Children)".
		const rest = books.slice(1);
		const pool = rest.some(isFullText) ? rest.filter(isFullText) : rest;
		shortBook = pool.sort((a, b) => wordsPerChapter(a) - wordsPerChapter(b))[0];
		picks.push({
			kind: 'shortRead',
			href: `/books/${shortBook.slug}/1`,
			title: shortBook.title,
			byline: shortBook.author.name,
			chapter: 1,
			language: shortBook.language,
			cover: toCoverFace(shortBook)
		});
	}

	const book = books.find((b) => b !== shortBook);
	if (book) {
		picks.push({
			kind: 'book',
			href: `/books/${book.slug}`,
			title: book.title,
			byline: book.author.name,
			language: book.language,
			cover: toCoverFace(book)
		});
	}

	const plan = need.plan ? plans.find((p) => p.slug === need.plan) : undefined;
	const article = topic.articles[0];
	// A person with a life — not an imprint byline — and not the book's writer.
	const author = topic.authors?.find((a) => !isImprint(a) && a.slug !== book?.author.slug);
	if (plan) {
		const lead = plan.covers[0];
		picks.push({
			kind: 'plan',
			href: `/plans/${plan.slug}`,
			title: plan.title,
			byline: '',
			language: plan.language,
			cover: (lead && tileFace(lead)) || undefined
		});
	} else if (article) {
		picks.push({
			kind: 'article',
			href: `/articles/${article.slug}/`,
			title: article.h1,
			byline: '',
			words: article.word_count,
			language: article.language,
			// Not the book pick's own cover twice in a row.
			cover: article.lead_book && article.lead_book.slug !== book?.slug ? article.lead_book : undefined
		});
	} else if (author) {
		picks.push({
			kind: 'life',
			href: authorPath(author.slug),
			title: author.name,
			byline:
				author.birth_year && author.death_year ? `${author.birth_year}–${author.death_year}` : '',
			language: topic.books[0]?.language ?? '',
			portrait: author
		});
	}

	return { topic: { slug: topic.slug, title: topic.title }, picks };
}

/** Plans per language, fetched once — every chip's third pick reads the same
 *  list. `null` is a failed fetch: forgotten here, and it keeps the picks it
 *  fed out of `loaded`, so the next press asks again. */
const planLists = new Map<string, Promise<PlanSummary[] | null>>();
/** Picks per language and situation, so a chip clicked again answers at once. */
const loaded = new Map<string, Promise<NeedPicks>>();

/**
 * The picks for `need` in `lang`, fetched on the chip's first press (the home
 * page is prerendered with no chip chosen, so it bakes no picks and hydration
 * waits on nothing). A failed fetch is forgotten, so pressing again retries.
 * The plan list is decoration: failing, it only drops the plan from these picks,
 * which are not kept, so the next press asks again.
 */
export function loadNeedPicks(need: Need, lang: string): Promise<NeedPicks> {
	const key = `${lang}:${need.id}`;
	let once = loaded.get(key);
	if (!once) {
		// Only a situation with a plan reads the plan list.
		let plans: Promise<PlanSummary[] | null> = Promise.resolve([]);
		if (need.plan) {
			let cached = planLists.get(lang);
			if (!cached) {
				cached = listPlans(lang).catch(() => {
					planLists.delete(lang);
					return null;
				});
				planLists.set(lang, cached);
			}
			plans = cached;
		}
		once = Promise.all([getTopic(need.topic, lang), plans]).then(([topic, list]) => {
			// Picks without the plan only because its list failed are shown, not kept.
			if (list === null) loaded.delete(key);
			return choosePicks(need, topic, list ?? []);
		});
		loaded.set(key, once);
		once.catch(() => loaded.delete(key));
	}
	return once;
}
