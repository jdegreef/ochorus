/**
 * Drafting a theological glossary with Claude, without an API key.
 *
 * Filling eleven pinned theological terms by hand is the slowest part of adding
 * a language, and the one most likely to be left half-done — which is the
 * expensive failure, because the translator then renders the missing terms
 * however it likes, book after book, and the output looks fine.
 *
 * There is no ANTHROPIC_API_KEY on the API service, so the admin cannot call a
 * model itself. Rather than add a secret, a per-call cost and a new failure mode
 * to the admin, this builds a prompt to run in Claude and parses the answer
 * back. The round trip is two clicks and needs no infrastructure.
 *
 * The prompt names the Bible the language is configured with, because that is
 * the wording the engine will quote verbatim — a glossary that disagrees with
 * its own Bible produces prose that contradicts the verses beside it.
 */

export interface GlossaryPromptInput {
	name: string;
	nativeName: string;
	bibleLabel?: string;
	bibleCode?: string;
	terms: string[];
}

/** The prompt to paste into Claude. */
export function buildGlossaryPrompt(input: GlossaryPromptInput): string {
	const { name, nativeName, bibleLabel, bibleCode, terms } = input;
	const language = nativeName.trim() ? `${name.trim()} (${nativeName.trim()})` : name.trim();
	const bible = (bibleLabel || '').trim() || (bibleCode || '').trim();

	return `You are helping build a theological glossary for Ochorus, a library of classic Christian devotional books (Andrew Murray, Charles Spurgeon, R. A. Torrey and their contemporaries) translated into many languages.

Target language: ${language || '(name the language)'}
${bible ? `Bible translation used for all scripture quotations: ${bible}\n` : ''}
These terms are PINNED: every book, sermon and biography in this language must word the doctrine the same way. Consistency across the whole library matters more than elegance in any one sentence.

For each English term below, give the rendering a careful translator of devotional prose would use in ${language || 'this language'}${bible ? `, matching the vocabulary of ${bible}` : ''}. Notes:

- Several entries are phrases, not single words ("the Holy Spirit", "the flesh", "the Lord"). Render them as they would naturally appear in running prose, including any article the language requires.
- "the flesh" is the theological sense (fallen human nature opposed to the Spirit), never the culinary one.
- "abide" is the sense of John 15 — remaining or dwelling in Christ.
- "surrender" is the devotional sense of yielding oneself to God.
- Where a language has both a churchly and a plain register, prefer the one an ordinary believer reads in their own Bible.

Reply with ONLY a JSON object — no commentary, no markdown fence — whose keys are EXACTLY the English terms below, unchanged:

${JSON.stringify(Object.fromEntries(terms.map((t) => [t, ''])), null, 2)}`;
}

export interface ParsedGlossary {
	values: Record<string, string>;
	filled: string[];
	missing: string[];
	unknown: string[];
	error?: string;
}

/**
 * Parse a pasted reply into glossary values.
 *
 * Deliberately tolerant of what a chat window actually produces — a ```json
 * fence, a sentence before the object, smart quotes from a copy-paste round
 * trip — because the alternative is a human retyping eleven fields over a
 * stray backtick. Strict about the KEYS, though: an unrecognised term is
 * reported rather than silently dropped, since a dropped key is exactly the
 * half-filled glossary this is meant to prevent.
 */
export function parseGlossaryReply(raw: string, terms: string[]): ParsedGlossary {
	const empty = { values: {}, filled: [], missing: [...terms], unknown: [] };
	const text = (raw || '').trim();
	if (!text) return { ...empty, error: 'Nothing pasted yet.' };

	// Strip a markdown fence, then take the outermost {...} so a stray
	// "Here you go:" preamble doesn't defeat the parse.
	let body = text.replace(/^\s*```(?:json)?\s*/i, '').replace(/\s*```\s*$/, '');
	// A top-level array is a plausible mistake ("give me a list of terms"), and
	// deserves a better message than "no JSON object found".
	if (body.trimStart().startsWith('[') && !body.includes('{')) {
		return { ...empty, error: 'Expected a JSON object of term → translation, not a list.' };
	}
	const start = body.indexOf('{');
	const end = body.lastIndexOf('}');
	if (start === -1 || end === -1 || end < start) {
		return { ...empty, error: 'No JSON object found in what was pasted.' };
	}
	body = body.slice(start, end + 1);

	let data: unknown;
	try {
		data = JSON.parse(body);
	} catch {
		// A copy-paste through a rich-text field can smarten the quotes; retry once.
		try {
			data = JSON.parse(body.replace(/[“”]/g, '"').replace(/[‘’]/g, "'"));
		} catch {
			return { ...empty, error: 'That is not valid JSON — paste the whole object, braces included.' };
		}
	}
	if (!data || typeof data !== 'object' || Array.isArray(data)) {
		return { ...empty, error: 'Expected a JSON object of term → translation.' };
	}

	const known = new Set(terms);
	const values: Record<string, string> = {};
	const unknown: string[] = [];
	for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
		const key = k.trim();
		if (!known.has(key)) {
			unknown.push(k);
			continue;
		}
		const val = typeof v === 'string' ? v.trim() : '';
		if (val) values[key] = val;
	}
	const filled = terms.filter((t) => values[t]);
	return { values, filled, missing: terms.filter((t) => !values[t]), unknown };
}
