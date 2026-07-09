import { browser } from '$app/environment';
import glossaryData from './glossary.json';

/**
 * Tap-to-define: definitions for a single selected word.
 *
 * Lookup order: (1) the curated Ochorus glossary — archaic and theological
 * terms as used in these classics — then (2) the free dictionaryapi.dev API.
 * Both failures (offline, unknown word) degrade to a gentle "no definition"
 * state; the reader never breaks. Results are cached per session.
 */

export interface Definition {
	word: string;
	source: 'glossary' | 'dictionary' | 'none';
	phonetic?: string;
	entries: { partOfSpeech?: string; text: string }[];
}

const glossary = glossaryData as Record<string, string>;

function glossaryLookup(word: string): string | null {
	if (word.startsWith('_')) return null;
	if (glossary[word]) return glossary[word];
	// Light stemming for plurals/possessives ("covenants", "sinner's").
	const stripped = word.replace(/['’]s$/, '').replace(/s$/, '');
	return glossary[stripped] ?? null;
}

const cache = new Map<string, Definition>();

async function dictionaryLookup(word: string): Promise<Definition | null> {
	const ctrl = new AbortController();
	const timer = setTimeout(() => ctrl.abort(), 4000);
	try {
		const res = await fetch(
			`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(word)}`,
			{ signal: ctrl.signal }
		);
		if (!res.ok) return null;
		const data = await res.json();
		const entry = Array.isArray(data) ? data[0] : null;
		if (!entry?.meanings?.length) return null;
		const entries = entry.meanings.slice(0, 2).map(
			(m: { partOfSpeech?: string; definitions?: { definition?: string }[] }) => ({
				partOfSpeech: m.partOfSpeech,
				text: m.definitions?.[0]?.definition ?? ''
			})
		).filter((e: { text: string }) => e.text);
		if (!entries.length) return null;
		return { word, source: 'dictionary', phonetic: entry.phonetic, entries };
	} catch {
		return null;
	} finally {
		clearTimeout(timer);
	}
}

class Define {
	open = $state(false);
	loading = $state(false);
	word = $state('');
	result = $state<Definition | null>(null);
	top = $state(0);
	left = $state(0);

	async show(rawWord: string, top: number, left: number) {
		if (!browser) return;
		const word = rawWord.toLowerCase().replace(/^[^a-z’']+|[^a-z’']+$/g, '');
		if (!word || word.length < 2) return;
		this.word = word;
		this.top = top;
		this.left = left;
		this.open = true;

		const cached = cache.get(word);
		if (cached) {
			this.result = cached;
			this.loading = false;
			return;
		}

		const gloss = glossaryLookup(word);
		if (gloss) {
			this.result = { word, source: 'glossary', entries: [{ text: gloss }] };
			cache.set(word, this.result);
			this.loading = false;
			return;
		}

		this.loading = true;
		this.result = null;
		const dict = await dictionaryLookup(word);
		// The reader may have selected a different word meanwhile.
		if (this.word !== word) return;
		this.result = dict ?? { word, source: 'none', entries: [] };
		cache.set(word, this.result);
		this.loading = false;
	}

	close() {
		this.open = false;
	}
}

export const define = new Define();
