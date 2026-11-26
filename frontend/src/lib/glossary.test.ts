import { describe, expect, it } from 'vitest';
import {
	FAITH_WORDS,
	GLOSSARY_TERMS,
	OLD_WORDS,
	byLetter,
	definitionOf,
	glossaryHref,
	glossaryTermFor,
	glossaryTermsIn,
	isGlossaryTerm,
	relatedTerms,
	titleCase
} from './glossary';

describe('glossary', () => {
	it('lists every term A–Z, without the file note', () => {
		expect(GLOSSARY_TERMS.length).toBeGreaterThan(100);
		expect(GLOSSARY_TERMS).not.toContain('_comment');
		expect(GLOSSARY_TERMS).toEqual([...GLOSSARY_TERMS].sort((a, b) => a.localeCompare(b, 'en')));
	});

	it('every term is a URL-safe slug with a definition', () => {
		for (const term of GLOSSARY_TERMS) {
			expect(term).toMatch(/^[a-z]+(-[a-z]+)*$/);
			expect(definitionOf(term)).not.toBe('');
		}
		expect(definitionOf('_comment')).toBe('');
		expect(glossaryHref('mercy-seat')).toBe('/glossary/mercy-seat/');
	});

	it('maps a word from the text to its entry', () => {
		expect(glossaryTermFor('wherefore')).toBe('wherefore');
		expect(glossaryTermFor('covenants')).toBe('covenant');
		expect(glossaryTermFor('pharisee’s')).toBe('pharisee');
		expect(glossaryTermFor('table')).toBeNull();
		expect(glossaryTermFor('_comment')).toBeNull();
	});

	it('groups by initial letter', () => {
		const groups = byLetter();
		expect(groups.flatMap((g) => g.terms)).toEqual(GLOSSARY_TERMS);
		for (const g of groups) for (const t of g.terms) expect(t[0].toUpperCase()).toBe(g.letter);
	});

	it('relates a term to its family, then its thematic neighbours', () => {
		const abide = relatedTerms('abide');
		expect(abide[0]).toBe('abideth');
		expect(abide).not.toContain('abide');
		expect(abide.length).toBe(6);
		expect(relatedTerms('circumcision')).toContain('uncircumcision');
		expect(relatedTerms('wherefore')).toEqual(expect.arrayContaining(['whence', 'wherein']));
		for (const t of GLOSSARY_TERMS) for (const r of relatedTerms(t)) expect(isGlossaryTerm(r)).toBe(true);
		expect(relatedTerms('nope')).toEqual([]);
	});

	it('titles a term', () => {
		expect(titleCase('wherefore')).toBe('Wherefore');
	});
});

describe('dictionary heads and shelves', () => {
	it('every term has a head, and the heads name only terms', async () => {
		const { GLOSSARY_TERMS, headOf } = await import('./glossary');
		const heads = (await import('./glossaryHeads.json')).default as Record<string, unknown>;
		for (const term of GLOSSARY_TERMS) expect(headOf(term), term).not.toBeNull();
		for (const k of Object.keys(heads)) if (!k.startsWith('_')) expect(GLOSSARY_TERMS).toContain(k);
	});
	it('the two shelves split the glossary between them', async () => {
		const { GLOSSARY_TERMS, OLD_WORDS, FAITH_WORDS } = await import('./glossary');
		expect(OLD_WORDS[0]).toBe('thou');
		expect(FAITH_WORDS[0]).toBe('covenant');
		expect(OLD_WORDS.length + FAITH_WORDS.length).toBe(GLOSSARY_TERMS.length);
	});
	it("a word's family", async () => {
		const { wordFamily } = await import('./glossary');
		expect(wordFamily('abase')).toEqual(['abasement']);
	});
});

describe('glossaryTermsIn', () => {
	it('finds the glossary words a chapter uses, doctrine before old English', () => {
		const faith = FAITH_WORDS[0];
		const old = OLD_WORDS[0];
		const html = `<p>${old} ${old} ${old} and ${faith}.</p>`;
		expect(glossaryTermsIn(html)).toEqual([faith, old]);
	});

	it('ranks by use, caps the list, and ignores markup and unknown words', () => {
		const [a, b] = FAITH_WORDS;
		const html = `<p class="${a}">${b} ${b} ${a} zzyzx</p>`;
		expect(glossaryTermsIn(html)).toEqual([b, a]);
		expect(glossaryTermsIn(html, 1)).toEqual([b]);
		expect(glossaryTermsIn('<p>nothing here</p>')).toEqual([]);
	});
});
