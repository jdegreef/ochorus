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

// The most slots any ONE kind may take, so a single import day cannot empty the
// feed of everything else. Content lands in batches — replaying the merge over
// the fixtures' created_at dates, 2026-09-16 produced a feed of 40 sermons and
// nothing else, 09-05 was 38 articles, and 09-04 left books at zero. It is not a
// property of articles, so it is not an articles-only rule: every kind is held
// to the same share, which also means a fourth kind needs no new judgement.
// Nothing is lost to crawlers either way — each kind has its own sitemap.
const MAX_PER_KIND = MAX_ITEMS / 2;


interface FeedItem {
	/** Which shelf this came from — the only thing `MAX_PER_KIND` counts. */
	kind: 'book' | 'sermon' | 'article';
	title: string;
	url: string;
	authorName: string;
	summary: string;
	/** ISO timestamp used for ordering and the entry's <updated>/<published>. */
	date: string;
}

/** Newest first. Guards rows whose date hasn't been served yet (API deploy
 *  race): they sort last, so a real date always wins the top. */
const byNewest = (a: FeedItem, b: FeedItem) => (b.date || '').localeCompare(a.date || '');

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

	const candidates: FeedItem[] = [
		...books.map((b) => ({
			kind: 'book' as const,
			title: b.title,
			url: `${SITE_URL}/books/${b.slug}/`,
			authorName: b.author.name,
			summary: b.subtitle || `A book by ${b.author.name}, free to read on Ochorus.`,
			date: b.created_at
		})),
		...sermons.map((s) => ({
			kind: 'sermon' as const,
			title: s.title,
			url: `${SITE_URL}/sermons/${s.slug}/`,
			authorName: s.author.name,
			summary: s.scripture_ref
				? `${s.author.name} on ${s.scripture_ref}.`
				: `A sermon by ${s.author.name}, free to read on Ochorus.`,
			date: s.created_at
		})),
		// `h1` is the display headline (the article page's warm H1), not
		// `meta_title`, which leads with the keyword for the <title>.
		...articles.map((a) => ({
			kind: 'article' as const,
			title: a.h1,
			url: `${SITE_URL}/articles/${a.slug}/`,
			// No per-article author FK — the house name is the byline the page
			// itself shows and the Article JSON-LD names. See the Article model.
			authorName: 'Ochorus',
			summary: a.description || 'An article from Ochorus.',
			date: a.created_at
		}))
	];

	// Newest first, then take the first MAX_ITEMS that keep every kind within
	// MAX_PER_KIND. One pass in date order, so the feed stays chronological (and
	// `updated` below stays the newest entry) while a batch day of one kind spills
	// into the others instead of taking the lot.
	const taken: Record<FeedItem['kind'], number> = { book: 0, sermon: 0, article: 0 };
	const items: FeedItem[] = [];
	for (const it of candidates.sort(byNewest)) {
		if (items.length >= MAX_ITEMS) break;
		if (taken[it.kind] >= MAX_PER_KIND) continue;
		taken[it.kind]++;
		items.push(it);
	}

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
