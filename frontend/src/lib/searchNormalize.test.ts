import { describe, it, expect } from 'vitest';
import { foldText, stemWord, normalizeForSearch, firstMatchSpan } from './searchNormalize';

describe('foldText', () => {
	it('case-folds, strips diacritics, straightens quotes', () => {
		expect(foldText('Béni')).toBe('beni');
		expect(foldText('DON’T')).toBe("don't");
		expect(foldText('“quote”')).toBe('"quote"');
	});
	it('is length-preserving for ASCII', () => {
		const s = "The Lord's promises";
		expect(foldText(s).length).toBe(s.length);
	});
});

describe('stemWord — canonical Porter vectors', () => {
	// From Porter's own sample vocabulary; validates the algorithm, not the
	// readability of the (never-shown) stems.
	const cases: [string, string][] = [
		['caresses', 'caress'],
		['ponies', 'poni'],
		['ties', 'ti'],
		['caress', 'caress'],
		['cats', 'cat'],
		['feed', 'feed'],
		['agreed', 'agre'],
		['plastered', 'plaster'],
		['bled', 'bled'],
		['motoring', 'motor'],
		['sing', 'sing'],
		['conflated', 'conflat'], // step 5a strips the e re-added in 1b (m>1)
		['troubled', 'troubl'],
		['sized', 'size'],
		['hopping', 'hop'],
		['tanned', 'tan'],
		['falling', 'fall'],
		['hissing', 'hiss'],
		['fizzed', 'fizz'],
		['failing', 'fail'],
		['filing', 'file'],
		['happy', 'happi'],
		['relational', 'relat'],
		['conditional', 'condit'],
		['rational', 'ration'],
		['callousness', 'callous'],
		['formalize', 'formal'],
		['goodness', 'good']
	];
	for (const [input, expected] of cases) {
		it(`${input} → ${expected}`, () => expect(stemWord(input)).toBe(expected));
	}
});

describe('stemWord — inflections fold onto one root (the search win)', () => {
	it('folds a verb family to one stem', () => {
		const family = ['pray', 'prays', 'praying', 'prayed'].map(stemWord);
		expect(new Set(family).size).toBe(1);
	});
	it('folds promise/promises/promised/promising to one stem', () => {
		const family = ['promise', 'promises', 'promised', 'promising'].map(stemWord);
		expect(new Set(family).size).toBe(1);
	});
	it('matches plural to singular', () => {
		expect(stemWord('prayers')).toBe(stemWord('prayer'));
		expect(stemWord('books')).toBe(stemWord('book'));
		expect(stemWord('graces')).toBe(stemWord('grace'));
	});
	it('keeps different roots distinct (server FTS handles those)', () => {
		expect(stemWord('praying')).not.toBe(stemWord('prayer'));
	});
});

describe('normalizeForSearch', () => {
	it('folds but does NOT stem non-English content', () => {
		const ar = 'الصلاة';
		expect(normalizeForSearch(ar, false)).toBe(ar);
		expect(normalizeForSearch('books', false)).toBe('books'); // suffix kept
	});
	it('stems each word for English content', () => {
		const a = normalizeForSearch('The Promises of God', true);
		const b = normalizeForSearch('a promise', true);
		expect(a.includes(normalizeForSearch('promise', true))).toBe(true);
		expect(b.includes(normalizeForSearch('promises', true))).toBe(true);
	});
});

describe('firstMatchSpan', () => {
	const text = 'He kept the promises and prayers.';
	it('locates the raw inflected word a stemmed query landed on', () => {
		const span = firstMatchSpan(text, 'prayer', true);
		expect(span).not.toBeNull();
		expect(text.slice(span![0], span![0] + span![1])).toBe('prayers.');
	});
	it('returns null when nothing matches', () => {
		expect(firstMatchSpan(text, 'zebra', true)).toBeNull();
	});
	it('substring-matches without stemming for non-English content', () => {
		expect(firstMatchSpan('livres ici', 'livre', false)).not.toBeNull();
	});
});
