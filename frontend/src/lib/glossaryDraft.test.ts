import { describe, expect, it } from 'vitest';
import { buildGlossaryPrompt, parseGlossaryReply } from './glossaryDraft';

const TERMS = ['justification', 'sanctification', 'the flesh', 'abide'];

describe('buildGlossaryPrompt', () => {
	it('names the language and every term, and asks for exact keys', () => {
		const p = buildGlossaryPrompt({
			name: 'Hindi',
			nativeName: 'हिन्दी',
			bibleLabel: 'Indian Revised Version',
			terms: TERMS
		});
		expect(p).toContain('Hindi (हिन्दी)');
		for (const t of TERMS) expect(p).toContain(t);
		expect(p).toContain('EXACTLY');
	});

	it('names the Bible, so the glossary agrees with the verses beside it', () => {
		const p = buildGlossaryPrompt({
			name: 'Hindi',
			nativeName: 'हिन्दी',
			bibleLabel: 'Indian Revised Version',
			terms: TERMS
		});
		expect(p).toContain('Indian Revised Version');
		expect(p).toMatch(/matching the vocabulary of/);
	});

	it('falls back to the bible CODE when no label is given, and omits the line entirely when neither is', () => {
		expect(buildGlossaryPrompt({ name: 'Hindi', nativeName: '', bibleCode: 'hin-irv', terms: TERMS })).toContain(
			'hin-irv'
		);
		const none = buildGlossaryPrompt({ name: 'Hindi', nativeName: '', terms: TERMS });
		expect(none).not.toContain('Bible translation used');
	});
});

describe('parseGlossaryReply', () => {
	const good = JSON.stringify({
		justification: 'धर्मी ठहराया जाना',
		sanctification: 'पवित्रीकरण',
		'the flesh': 'शरीर',
		abide: 'बने रहना'
	});

	it('parses a clean object', () => {
		const r = parseGlossaryReply(good, TERMS);
		expect(r.error).toBeUndefined();
		expect(r.filled).toEqual(TERMS);
		expect(r.missing).toEqual([]);
		expect(r.values['the flesh']).toBe('शरीर');
	});

	it('survives a markdown fence and a chatty preamble', () => {
		const r = parseGlossaryReply('Sure! Here you go:\n\n```json\n' + good + '\n```', TERMS);
		expect(r.error).toBeUndefined();
		expect(r.filled).toEqual(TERMS);
	});

	it('recovers from smart quotes introduced by a copy-paste round trip', () => {
		const smart = good.replace(/"/g, '”');
		expect(parseGlossaryReply(smart, TERMS).filled).toEqual(TERMS);
	});

	it('reports missing terms rather than silently accepting a partial glossary', () => {
		const r = parseGlossaryReply(JSON.stringify({ justification: 'x' }), TERMS);
		expect(r.filled).toEqual(['justification']);
		expect(r.missing).toEqual(['sanctification', 'the flesh', 'abide']);
	});

	it('reports unknown keys instead of dropping them quietly', () => {
		const r = parseGlossaryReply(JSON.stringify({ justification: 'x', redemption: 'y' }), TERMS);
		expect(r.unknown).toEqual(['redemption']);
		expect(r.values.redemption).toBeUndefined();
	});

	it('treats a blank value as missing, not as filled', () => {
		const r = parseGlossaryReply(JSON.stringify({ justification: '   ' }), TERMS);
		expect(r.filled).toEqual([]);
		expect(r.missing).toContain('justification');
	});

	it('explains itself on junk input rather than throwing', () => {
		expect(parseGlossaryReply('', TERMS).error).toMatch(/Nothing pasted/);
		expect(parseGlossaryReply('no json here', TERMS).error).toMatch(/No JSON object/);
		expect(parseGlossaryReply('{ nope: }', TERMS).error).toMatch(/not valid JSON/);
		expect(parseGlossaryReply('[1,2]', TERMS).error).toMatch(/object of term/);
	});
});
