import { SITE_URL } from '$lib/config';
import { FEED_EPOCH, isoOrEpoch } from '$lib/feedDate';
import { listArticles, listBooks, listSermons } from '$lib/library-public';
import { xmlEscape as xml } from '$lib/xml';

export const prerender = true;

// A single English Atom feed of the newest works added to the library, so
// readers (and aggregators) can subscribe to "what's new on Ochorus". English
// is the canonical feed — the site is multilingual per-row, but one feed keeps
// subscriptions simple; a per-locale feed can follow if there's demand.
//
// Ordered by created_at (when a work was added to Ochorus), newest first —
// NOT by the work's original date, which for public-domain classics is a
// century old and would never change. Books carry created_at directly;
// sermons gained it on their list serializer for this feed.
//
// Articles ride along for the same reason the sitemap lists them on their own
// line: they are the discovery layer, and until now the one syndication surface
// the site has did not mention them at all. English only, like the feed and
// like the articles themselves.

const MAX_ITEMS = 40;

// How many of those items an article may take. Articles ship in CURATED BATCHES
// (75 landed over 2026-09-03..05, another 54 on 09-18), and a plain merge by
// date would let one batch day evict every book and sermon from a feed titled
// "New in the Library" — the subscriber would see a wall of essays and no works
// until the next import. Reserving the balance keeps the feed answering the
// question it asks. Articles beyond the cap are not lost to crawlers: every one
// is in sitemap-articles.xml and linked from the /articles/ hub.
const MAX_ARTICLES = 12;


interface FeedItem {
	title: string;
	url: string;
	authorName: string;
	summary: string;
	/** ISO timestamp used for ordering and the entry's <updated>/<published>. */
	date: string;
}

function entryXml(it: FeedItem): string {
	const updated = isoOrEpoch(it.date);
	return [
		'  <entry>',
		`    <title>${xml(it.title)}</title>`,
		`    <link href="${xml(it.url)}"/>`,
		`    <id>${xml(it.url)}</id>`,
		`    <updated>${updated}</updated>`,
		`    <published>${updated}</published>`,
		`    <author><name>${xml(it.authorName)}</name></author>`,
		`    <summary>${xml(it.summary)}</summary>`,
		'  </entry>'
	].join('\n');
}

export async function GET() {
	// A down endpoint degrades to an empty slice rather than failing the whole
	// prerender (mirrors the sitemap).
	const [books, sermons, articles] = await Promise.all([
		listBooks('en').catch(() => []),
		listSermons('en').catch(() => []),
		listArticles('en').catch(() => [])
	]);

	const items: FeedItem[] = [
		...books.map((b) => ({
			title: b.title,
			url: `${SITE_URL}/books/${b.slug}/`,
			authorName: b.author.name,
			summary: b.subtitle || `A book by ${b.author.name}, free to read on Ochorus.`,
			date: b.created_at
		})),
		...sermons.map((s) => ({
			title: s.title,
			url: `${SITE_URL}/sermons/${s.slug}/`,
			authorName: s.author.name,
			summary: s.scripture_ref
				? `${s.author.name} on ${s.scripture_ref}.`
				: `A sermon by ${s.author.name}, free to read on Ochorus.`,
			date: s.created_at
		})),
		// Newest-first, then capped, BEFORE the merge — so the cap keeps the
		// newest articles rather than whichever ones the merged sort happens to
		// leave standing. `h1` is the display headline (the article page's warm
		// H1), not `meta_title`, which leads with the keyword for the <title>.
		...articles
			.slice()
			.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
			.slice(0, MAX_ARTICLES)
			.map((a) => ({
				title: a.h1,
				url: `${SITE_URL}/articles/${a.slug}/`,
				// No per-article author FK — the house name is the byline the page
				// itself shows and the Article JSON-LD names. See the Article model.
				authorName: 'Ochorus',
				summary: a.description || 'An article from Ochorus.',
				date: a.created_at
			}))
	]
		// Guard against rows whose date hasn't been served yet (API deploy race):
		// keep them, but sort undated last so a real date always wins the top.
		.sort((a, b) => (b.date || '').localeCompare(a.date || ''))
		.slice(0, MAX_ITEMS);

	// Feed <updated> is the newest entry's timestamp — stable across rebuilds
	// (no wall-clock), so the feed only changes when the content does.
	const updated = items.length ? isoOrEpoch(items[0].date) : FEED_EPOCH;

	const body = [
		'<?xml version="1.0" encoding="utf-8"?>',
		'<feed xmlns="http://www.w3.org/2005/Atom">',
		'  <title>Ochorus — New in the Library</title>',
		'  <subtitle>Free public-domain Christian classics: books, sermons and articles.</subtitle>',
		`  <link href="${SITE_URL}/feed.xml" rel="self"/>`,
		`  <link href="${SITE_URL}/"/>`,
		`  <id>${SITE_URL}/</id>`,
		`  <updated>${updated}</updated>`,
		...items.map(entryXml),
		'</feed>',
		''
	].join('\n');

	return new Response(body, {
		headers: { 'content-type': 'application/atom+xml; charset=utf-8' }
	});
}
