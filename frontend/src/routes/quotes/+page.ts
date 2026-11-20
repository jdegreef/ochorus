import { getQuoteTopicPage, listFeaturedQuotes, listQuoteAuthors, listQuoteTopics } from '$lib/library-public';
import { wallTopic } from '$lib/quoteWall';
import { loadShelf } from '$lib/loadShelf';
import { dayIndex } from '$lib/quoteText';
import type { PageLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

// English-only, like the author quote pages it links to: the quotations are
// lifted from the English works, so there is no translated index to serve. The
// list comes from the same endpoint the author-page entry generator and the
// sitemap read, so all three advertise exactly the reviewed set.
//
// The quote themes ride along for the topic chips — the page's second way in.
// A failed topic fetch only hides the chips; the authors decide the error state.
const WALL_TOPICS = 6;

export const load: PageLoad = async ({ fetch }) => {
	const [authors, topics, featured] = await Promise.all([
		loadShelf(listQuoteAuthors(fetch)),
		loadShelf(listQuoteTopics(fetch)),
		// The lead quotation's pool; a failed fetch just leaves the page without it.
		loadShelf(listFeaturedQuotes(fetch))
	]);
	// The wall of lines: the first few themes (the API's curated order), each
	// as its shortest lines. Decoration — a failed theme just drops out.
	// Fetched together, laid out in order, so a line on two themes stays under
	// the first.
	const pages = await Promise.all(
		topics.items.slice(0, WALL_TOPICS).map((tp) => getQuoteTopicPage(tp.slug, fetch).catch(() => null))
	);
	const seen = new Set<string>();
	const wall = pages
		.map((p) => (p ? wallTopic(p, 3, seen) : null))
		.filter((w) => w && w.lines.length >= 2);
	return {
		wall: wall as NonNullable<(typeof wall)[number]>[],
		authors: authors.items,
		loadError: authors.loadError,
		topics: topics.items,
		featured: featured.items,
		// The day's pick AS OF THE BUILD, baked into the prerendered page, so the
		// HTML and the browser agree and the lead quote only changes after load
		// when the day has turned since the deploy.
		featuredAt: dayIndex(new Date(), featured.items.length)
	};
};
