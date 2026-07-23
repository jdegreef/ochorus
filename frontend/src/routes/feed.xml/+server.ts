import { SITE_URL } from '$lib/config';
import { listBooks, listSermons } from '$lib/library';

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

const MAX_ITEMS = 40;

/** Escape the five XML predefined entities for text and attribute values. */
function xml(s: string): string {
	return s
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&apos;');
}

interface FeedItem {
	title: string;
	url: string;
	authorName: string;
	summary: string;
	/** ISO timestamp used for ordering and the entry's <updated>/<published>. */
	date: string;
}

function entryXml(it: FeedItem): string {
	const updated = new Date(it.date).toISOString();
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
	const [books, sermons] = await Promise.all([
		listBooks('en').catch(() => []),
		listSermons('en').catch(() => [])
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
		}))
	]
		// Guard against rows whose date hasn't been served yet (API deploy race):
		// keep them, but sort undated last so a real date always wins the top.
		.sort((a, b) => (b.date || '').localeCompare(a.date || ''))
		.slice(0, MAX_ITEMS);

	// Feed <updated> is the newest entry's timestamp — stable across rebuilds
	// (no wall-clock), so the feed only changes when the content does.
	const updated = items.length ? new Date(items[0].date).toISOString() : '1970-01-01T00:00:00Z';

	const body = [
		'<?xml version="1.0" encoding="utf-8"?>',
		'<feed xmlns="http://www.w3.org/2005/Atom">',
		'  <title>Ochorus — New in the Library</title>',
		'  <subtitle>Free public-domain Christian classics: books and sermons.</subtitle>',
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
