import { isBibleBook } from './bible';
import { SITE_URL } from './config';
import { stripHtml, truncateMeta } from './seo';

/**
 * /llms.txt and /llms-full.txt — a plain-Markdown map of the site for AI
 * assistants and answer engines (the llmstxt.org convention): what Ochorus is,
 * where each shelf lives, and how to cite it. Crawlers can read every page
 * already; this is the one file an assistant fetches to understand the whole
 * site at once, so it names the entities (authors, topics, articles, books) an
 * answer would link to.
 *
 * Pure: the routes fetch the rows and hand them here, so the output is tested
 * without the API. English only, like the scripture and quote graphs — the
 * locale home pages are listed so an assistant can send a reader to their
 * language.
 */

export interface LlmsAuthor {
	slug: string;
	name: string;
	bio: string;
	birth_year: number | null;
	death_year: number | null;
	book_count: number;
	sermon_count: number;
}
export interface LlmsTopic {
	slug: string;
	title: string;
	description: string;
}
export interface LlmsArticle {
	slug: string;
	h1: string;
	description: string;
}
export interface LlmsBook {
	slug: string;
	title: string;
	subtitle: string;
	hook?: string;
	chapter_count: number;
	author: { slug: string; name: string };
	series?: { slug: string } | null;
}
export interface LlmsSermon {
	slug: string;
	title: string;
	scripture_ref: string;
	summary: string;
	author: { name: string };
}

export interface LlmsData {
	authors: LlmsAuthor[];
	topics: LlmsTopic[];
	articles: LlmsArticle[];
	/** Live locales other than English, as [code, autonym]. */
	locales: [string, string][];
	books?: LlmsBook[];
	sermons?: LlmsSermon[];
}

const url = (path: string) => `${SITE_URL}${path}`;

/** One line, markdown-safe: no brackets to break a link, no newlines. */
const line = (s: string, max = 200) => truncateMeta(stripHtml(s ?? '').replace(/[[\]]/g, ''), max);

const years = (a: LlmsAuthor) =>
	a.birth_year || a.death_year ? ` (${a.birth_year ?? '?'}–${a.death_year ?? ''})` : '';

const item = (name: string, path: string, note = '') =>
	`- [${name.replace(/[[\]]/g, '')}](${url(path)})${note ? `: ${note}` : ''}`;

export const LLMS_SUMMARY =
	'Ochorus is a free online library of classic Christian books, sermons and biographies — ' +
	'public-domain works by writers such as Andrew Murray, Charles H. Spurgeon, E. M. Bounds and ' +
	'Augustine — set for easy reading on the web and in phone apps, in many languages. It is a ' +
	'ministry founded in 2021, based in Victoria, Canada and Kampala, Uganda. ' +
	'Everything is free to read, with no account needed.';

function header(): string[] {
	return [
		'# Ochorus',
		'',
		`> ${LLMS_SUMMARY}`,
		'',
		'The classic texts are in the public domain; each page says so in its "About this text" ' +
			'note and in its JSON-LD `license`. English Scripture is the Open Word Bible (CC0). ' +
			'Ochorus Originals are new books written by Ochorus and are not public domain. ' +
			'Every book, chapter, sermon and biography has its own stable URL ending in a slash.',
		'',
		'When citing, link the chapter or sermon page and name the author and work, for example: ' +
			`"Andrew Murray, Humility, ch. 1 (Ochorus, ${url('/books/humility-2/1/')})".`,
		''
	];
}

function sections(): string[] {
	return [
		'## Start here',
		'',
		item('Books', '/books/', 'every classic book, by author, topic and length'),
		item('Sermons', '/sermons/', 'classic sermons, each with a short summary and study questions'),
		item(
			'Authors and biographies',
			'/biographies/',
			'long-form lives of the preachers, missionaries and writers'
		),
		item('Topics', '/topics/', 'books and sermons gathered by subject'),
		item(
			'Articles',
			'/articles/',
			'answers to common questions about the Christian faith, each leading into the classics'
		),
		item('Bible', '/bible/', 'the Open Word Bible, chapter by chapter'),
		item(
			'Scripture in the classics',
			'/scripture/',
			'for each Bible chapter, the passages of the classics that discuss it'
		),
		item('Quotes', '/quotes/', 'quotations from the authors, each linked to its source chapter'),
		item('Reading plans', '/plans/', 'guided journeys through the books, a chapter a day'),
		item('Glossary', '/glossary/', 'old words found in the Bible and the classics, explained'),
		item('Young readers', '/young-readers/', 'retellings of the classics for children and teens'),
		item('Ochorus Originals', '/originals/', 'new books written by Ochorus'),
		item('About Ochorus', '/about/'),
		''
	];
}

function languages(locales: [string, string][]): string[] {
	if (!locales.length) return [];
	return [
		'## Languages',
		'',
		'Each language has its own pages under a prefix. A work appears only in the languages it has been published in.',
		'',
		...locales.map(([code, name]) => item(name, `/${code}/`)),
		''
	];
}

function authorLines(authors: LlmsAuthor[]): string[] {
	const listed = authors
		.filter((a) => a.book_count + a.sermon_count > 0)
		.sort((a, b) => a.name.localeCompare(b.name));
	if (!listed.length) return [];
	return [
		'## Authors',
		'',
		...listed.map((a) => item(`${a.name}${years(a)}`, `/authors/${a.slug}/`, line(a.bio, 160))),
		''
	];
}

function topicLines(topics: LlmsTopic[]): string[] {
	if (!topics.length) return [];
	return [
		'## Topics',
		'',
		...topics.map((t) => item(t.title, `/topics/${t.slug}/`, line(t.description, 160))),
		''
	];
}

function articleLines(articles: LlmsArticle[]): string[] {
	if (!articles.length) return [];
	return [
		'## Articles',
		'',
		...articles.map((a) => item(a.h1, `/articles/${a.slug}/`, line(a.description, 160))),
		''
	];
}

function bookLines(books: LlmsBook[]): string[] {
	const works = books.filter((b) => !isBibleBook(b));
	if (!works.length) return [];
	const byAuthor = new Map<string, LlmsBook[]>();
	for (const b of works) {
		const list = byAuthor.get(b.author.name) ?? [];
		list.push(b);
		byAuthor.set(b.author.name, list);
	}
	const out = ['## Books', ''];
	for (const name of [...byAuthor.keys()].sort((a, b) => a.localeCompare(b))) {
		out.push(`### ${name}`, '');
		for (const b of byAuthor.get(name)!.sort((x, y) => x.title.localeCompare(y.title))) {
			const note = [
				line(b.hook || b.subtitle, 160),
				b.chapter_count ? `${b.chapter_count} chapters` : ''
			]
				.filter(Boolean)
				.join(' · ');
			out.push(item(b.title, `/books/${b.slug}/`, note));
		}
		out.push('');
	}
	return out;
}

function sermonLines(sermons: LlmsSermon[]): string[] {
	if (!sermons.length) return [];
	const sorted = [...sermons].sort(
		(a, b) => a.author.name.localeCompare(b.author.name) || a.title.localeCompare(b.title)
	);
	return [
		'## Sermons',
		'',
		...sorted.map((s) =>
			item(
				`${s.title} — ${s.author.name}`,
				`/sermons/${s.slug}/`,
				[s.scripture_ref, line(s.summary, 160)].filter(Boolean).join(' · ')
			)
		),
		''
	];
}

/** The short map: summary, shelves, languages, authors, topics, articles. */
export function buildLlmsTxt(d: LlmsData): string {
	return [
		...header(),
		...sections(),
		...languages(d.locales),
		...topicLines(d.topics),
		...authorLines(d.authors),
		...articleLines(d.articles),
		'## Optional',
		'',
		item('Full index', '/llms-full.txt', 'every English book and sermon, with a line on each'),
		item('Sitemap', '/sitemap.xml'),
		''
	].join('\n');
}

/** The long index: everything in llms.txt plus every English book and sermon. */
export function buildLlmsFullTxt(d: LlmsData): string {
	return [
		...header(),
		...sections(),
		...languages(d.locales),
		...topicLines(d.topics),
		...authorLines(d.authors),
		...articleLines(d.articles),
		...bookLines(d.books ?? []),
		...sermonLines(d.sermons ?? [])
	].join('\n');
}
