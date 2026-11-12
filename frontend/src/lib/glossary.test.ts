import { describe, expect, it } from 'vitest';
import {
	GLOSSARY_TERMS,
	byLetter,
	definitionOf,
	glossaryHref,
	glossaryTermFor,
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
