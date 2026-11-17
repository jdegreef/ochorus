import { ADVERTISED_LOCALES } from './advertised-locales';
import { localeName } from './lang.svelte';
import { listArticles, listAuthors, listBooks, listSermons, listTopics } from './library-public';
import type { LlmsData } from './llmsTxt';

/**
 * The rows /llms.txt and /llms-full.txt are built from, fetched at prerender.
 * A down endpoint degrades to an empty section rather than failing the build
 * (mirrors the feed and the sitemap).
 */
export async function loadLlmsData(full: boolean): Promise<LlmsData> {
	const [authors, topics, articles, books, sermons] = await Promise.all([
		listAuthors('en').catch(() => []),
		listTopics('en').catch(() => []),
		listArticles('en').catch(() => []),
		full ? listBooks('en').catch(() => []) : Promise.resolve([]),
		full ? listSermons('en').catch(() => []) : Promise.resolve([])
	]);
	return {
		authors,
		topics,
		articles,
		books,
		sermons,
		locales: ADVERTISED_LOCALES.filter((l) => l !== 'en').map((l) => [l, localeName(l)])
	};
}
