import { describe, expect, it } from 'vitest';
import { findQueryHits, queryWords } from './searchHits';
import { renderMarks } from './rangeMarks';

/**
 * Landing on the match.
 *
 * Two halves, tested separately because they fail differently. `findQueryHits`
 * is pure arithmetic on strings — wrong offsets highlight the wrong words. The
 * rendering half edits a chapter's DOM, and chapter bodies are server-sanitised
 * HTML the reader trusts: the standing risk is that decorating them corrupts
 * the markup, or worse, becomes a way to inject through the one surface the
 * sanitiser exists to protect. So the structural invariants are asserted, not
 * assumed.
 */

describe('queryWords', () => {
	it('lowercases and splits', () => {
		expect(queryWords('Prayer Life')).toEqual(['prayer', 'life']);
	});

	it('drops the websearch operators rather than searching for them', () => {
		// `prayer -healing` means the word prayer, not the punctuation.
		expect(queryWords('"secret place" OR -healing')).toEqual([
			'secret',
			'place',
			'healing'
		]);
	});

	it('ignores single characters, which would match everywhere', () => {
		expect(queryWords('a I of')).toEqual(['of']);
	});

	it('survives an empty or whitespace query', () => {
		expect(queryWords('')).toEqual([]);
		expect(queryWords('   ')).toEqual([]);
	});
});

describe('findQueryHits', () => {
	const blocks = ['Humility is the place of entire dependence on God.', 'Pride must die.'];

	it('finds a word and reports its offsets', () => {
		expect(findQueryHits(blocks, 'humility')).toEqual([{ p: 0, s: 0, e: 8 }]);
	});

	it('is case-insensitive', () => {
		expect(findQueryHits(blocks, 'HUMILITY')).toEqual([{ p: 0, s: 0, e: 8 }]);
	});

	it('indexes the block the match is in', () => {
		expect(findQueryHits(blocks, 'pride')).toEqual([{ p: 1, s: 0, e: 5 }]);
	});

	it('finds every occurrence, not just the first', () => {
		expect(findQueryHits(['one two one two one'], 'one')).toHaveLength(3);
	});

	it('merges overlapping matches so nothing is wrapped twice', () => {
		// "depend" and "dependence" overlap; wrapping both would nest marks.
		const hits = findQueryHits(blocks, 'depend dependence');
		expect(hits).toEqual([{ p: 0, s: 32, e: 42 }]);
	});

	it('returns nothing for a query the text does not contain', () => {
		// The server stems ("praying" matches "prayer"); this does not, so a
		// result can legitimately open with no highlight. That is the documented
		// behaviour, not a bug — guessing at stems would highlight wrong words.
		expect(findQueryHits(blocks, 'praying')).toEqual([]);
	});

	it('caps the number of hits', () => {
		const many = Array.from({ length: 500 }, () => 'prayer');
		expect(findQueryHits(many, 'prayer').length).toBeLessThanOrEqual(200);
	});
});

describe('rendering hits into a chapter', () => {
	function chapter(html: string) {
		const el = document.createElement('div');
		el.className = 'reading';
		el.innerHTML = html;
		return el;
	}
	const HTML =
		'<p>Humility is the <em>place</em> of dependence.</p><blockquote>Pride must die.</blockquote>';

	it('wraps the match and leaves the element structure alone', () => {
		const el = chapter(HTML);
		const before = el.querySelectorAll('p, em, blockquote').length;
		renderMarks(el, [], () => {}, findQueryHits(['Humility is the place of dependence.'], 'humility'));
		expect(el.querySelectorAll('mark.search-hit')).toHaveLength(1);
		expect(el.querySelector('mark.search-hit')?.textContent).toBe('Humility');
		expect(el.querySelectorAll('p, em, blockquote').length).toBe(before);
	});

	it('spans an inline element without breaking it', () => {
		// "the place of" crosses into and out of the <em>. The wrap must split
		// text nodes, never re-serialise the HTML.
		const el = chapter(HTML);
		renderMarks(el, [], () => {}, findQueryHits(['Humility is the place of dependence.'], 'place'));
		expect(el.querySelector('em')).not.toBeNull();
		expect(el.querySelector('em mark.search-hit')?.textContent).toBe('place');
	});

	it('never treats the query as markup', () => {
		// The query reaches this code from a URL. If it were ever concatenated
		// into HTML, this is the test that would fail.
		const el = chapter('<p>A tag like &lt;img&gt; is just text.</p>');
		renderMarks(el, [], () => {}, findQueryHits(['A tag like <img> is just text.'], '<img onerror=x>'));
		expect(el.querySelector('img')).toBeNull();
		expect(el.innerHTML).not.toContain('onerror');
	});

	it('restores the original HTML when the hits go away', () => {
		// The invariant that makes this safe to run repeatedly: decorating and
		// then un-decorating is the identity. `data-pristine` is the renderer's
		// own bookkeeping — it is how the restore is possible — so it is stripped
		// before comparing rather than counted as a difference.
		const strip = (root: HTMLElement) => {
			const clone = root.cloneNode(true) as HTMLElement;
			clone.querySelectorAll('[data-pristine]').forEach((n) => n.removeAttribute('data-pristine'));
			return clone.innerHTML;
		};
		const el = chapter(HTML);
		const original = el.innerHTML;
		renderMarks(el, [], () => {}, findQueryHits(['Humility is the place of dependence.'], 'humility'));
		expect(el.querySelectorAll('mark')).toHaveLength(1);
		renderMarks(el, [], () => {}, []);
		expect(el.querySelectorAll('mark')).toHaveLength(0);
		expect(strip(el)).toBe(original);
	});

	it('does not nest marks when rendered twice', () => {
		const el = chapter(HTML);
		const hits = findQueryHits(['Humility is the place of dependence.'], 'humility');
		renderMarks(el, [], () => {}, hits);
		renderMarks(el, [], () => {}, hits);
		expect(el.querySelectorAll('mark.search-hit')).toHaveLength(1);
		expect(el.querySelector('mark.search-hit mark')).toBeNull();
	});

	it('coexists with a persisted highlight', () => {
		// The two decorate the same paragraph through one renderer; a search hit
		// must not be clickable or carry a mark id.
		const el = chapter(HTML);
		renderMarks(
			el,
			[{ id: 'm1', p: 1, s: 0, e: 5 }],
			() => {},
			findQueryHits(['Humility is the place of dependence.'], 'humility')
		);
		expect(el.querySelector('mark.range-mark')?.textContent).toBe('Pride');
		expect(el.querySelector('mark.search-hit')?.textContent).toBe('Humility');
		expect(el.querySelector('mark.search-hit')?.getAttribute('data-mark-id')).toBeNull();
	});
});
