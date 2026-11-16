import { track } from './analytics';

/**
 * Which AI assistant sent this visit, if any — so answer-engine traffic can be
 * counted as a channel (Plausible goal `AI referral`) instead of being lost
 * among a hundred referrer hosts. That is how we learn whether the AEO work
 * (llms.txt, Q&A, FAQPage markup) is reaching anyone.
 *
 * Two signals, either one enough: the referrer's host, and the `utm_source`
 * an assistant stamps on its citation links (ChatGPT adds
 * `utm_source=chatgpt.com`, Perplexity and Copilot sometimes send no referrer
 * at all from their apps).
 *
 * The event carries the assistant's name and the KIND of page landed on —
 * short labels only, never the URL (see `track`).
 */

const ASSISTANTS: [RegExp, string][] = [
	[/(^|\.)chatgpt\.com$|(^|\.)openai\.com$/, 'ChatGPT'],
	[/(^|\.)perplexity\.ai$/, 'Perplexity'],
	[/(^|\.)gemini\.google\.com$|(^|\.)bard\.google\.com$/, 'Gemini'],
	[/(^|\.)copilot\.microsoft\.com$|(^|\.)copilot\.cloud\.microsoft$/, 'Copilot'],
	[/(^|\.)claude\.ai$/, 'Claude'],
	[/(^|\.)you\.com$/, 'You.com'],
	[/(^|\.)phind\.com$/, 'Phind'],
	[/(^|\.)meta\.ai$/, 'Meta AI'],
	[/(^|\.)chat\.deepseek\.com$/, 'DeepSeek'],
	[/(^|\.)grok\.com$/, 'Grok'],
	[/(^|\.)chat\.mistral\.ai$/, 'Mistral']
];

/** The assistant a host (or a bare utm_source value like `chatgpt.com`) names. */
export function assistantFor(host: string): string | null {
	const h = host
		.trim()
		.toLowerCase()
		.replace(/^www\./, '');
	if (!h) return null;
	for (const [re, name] of ASSISTANTS) if (re.test(h)) return name;
	return null;
}

/** The kind of page a path is — the event's `page` prop. */
export function pageKind(pathname: string): string {
	// Drop a locale prefix (/es/, /pt/…) so a localized page counts as its kind.
	const p = pathname.replace(/^\/[a-z]{2}(?=\/)/, '');
	if (p === '/' || p === '') return 'home';
	if (/^\/books\/[^/]+\/(modern\/)?\d+\/?$/.test(p)) return 'chapter';
	const first = p.split('/')[1];
	const kinds: Record<string, string> = {
		books: 'book',
		sermons: 'sermon',
		authors: 'author',
		biographies: 'biographies',
		articles: 'article',
		topics: 'topic',
		scripture: 'scripture',
		bible: 'bible',
		quotes: 'quote',
		plans: 'plan',
		glossary: 'glossary'
	};
	return kinds[first] ?? 'other';
}

/** The assistant behind a landing, from its referrer and URL; null if none. */
export function aiReferral(referrer: string, url: URL): string | null {
	let fromReferrer: string | null = null;
	try {
		fromReferrer = referrer ? assistantFor(new URL(referrer).hostname) : null;
	} catch {
		fromReferrer = null;
	}
	return fromReferrer ?? assistantFor(url.searchParams.get('utm_source') ?? '');
}

/**
 * Report the landing once per document load. A SPA navigation keeps the same
 * `document.referrer`, so this runs from the root layout's mount only.
 */
export function reportAiReferral(): void {
	const assistant = aiReferral(document.referrer, new URL(location.href));
	if (assistant) track('AI referral', { assistant, page: pageKind(location.pathname) });
}
