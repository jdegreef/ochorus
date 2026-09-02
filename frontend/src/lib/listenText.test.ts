import { describe, it, expect } from 'vitest';
import { spokenText, readerProse, blankFootnoteMarkers } from './listenText';

/** Build a prose block from an HTML string, the way the reader body holds one. */
function block(html: string): HTMLElement {
	const el = document.createElement('p');
	el.innerHTML = html;
	return el;
}

describe('spokenText', () => {
	it('drops a numbered footnote superscript', () => {
		expect(spokenText(block('first did meet with grace;<sup>4</sup>'))).toBe(
			'first did meet with grace;'
		);
	});

	it('drops an empty footnote superscript', () => {
		expect(spokenText(block('its course towards its centre,<sup></sup>'))).toBe(
			'its course towards its centre,'
		);
	});

	it('drops inline [1]/[a] footnote reference markers', () => {
		expect(spokenText(block('a prayer that availeth much.[2]'))).toBe('a prayer that availeth much.');
		expect(spokenText(block('the promise[a] of the gift'))).toBe('the promise of the gift');
	});

	it("keeps a multi-letter bracket — it's the editor's inserted word, not a marker", () => {
		expect(spokenText(block('he gave [him] grace'))).toBe('he gave [him] grace');
	});

	it("keeps a single UPPERCASE bracket — an inserted word or roman numeral, not a footnote letter", () => {
		// Footnote letters are lowercase ([a], [b]); "[I]" is the pronoun/roman
		// the editor inserted, and reading "he gave I grace" would be right.
		expect(spokenText(block('and [I] said to them'))).toBe('and [I] said to them');
	});

	it('keeps scripture references, which are prose to be read', () => {
		expect(spokenText(block('See <span class="scripture-ref">John 3:16</span> today'))).toBe(
			'See John 3:16 today'
		);
	});

	it('drops aria-hidden content', () => {
		expect(spokenText(block('word<span aria-hidden="true">✦</span> more'))).toBe('word more');
	});

	it('collapses whitespace and separates block children', () => {
		const bq = document.createElement('blockquote');
		bq.innerHTML = '<p>One sentence.</p>\n  <p>Two sentence.</p>';
		expect(spokenText(bq)).toBe('One sentence. Two sentence.');
	});

	it('treats <br> as a word break', () => {
		expect(spokenText(block('line one<br>line two'))).toBe('line one line two');
	});

	it('returns empty string for a whitespace-only block (reader skips these)', () => {
		expect(spokenText(block('   <sup></sup>  '))).toBe('');
	});
});

describe('readerProse — the shareable-quote path', () => {
	/** A cloned selection range arrives as a DocumentFragment, not an element. */
	function fragment(html: string): DocumentFragment {
		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		return tpl.content;
	}

	it('strips a <sup> marker from a fragment (the quote card leak)', () => {
		expect(readerProse(fragment('first did meet with grace;<sup>4</sup>'))).toBe(
			'first did meet with grace;'
		);
	});

	it('strips inline [4] markers from a fragment', () => {
		expect(readerProse(fragment('a prayer that availeth much.[4]'))).toBe(
			'a prayer that availeth much.'
		);
	});

	it('keeps the editor’s multi-letter bracket', () => {
		expect(readerProse(fragment('he gave [him] grace'))).toBe('he gave [him] grace');
	});
});

describe('blankFootnoteMarkers — the offset-pinned path', () => {
	function block(html: string): HTMLElement {
		const el = document.createElement('p');
		el.innerHTML = html;
		return el;
	}

	it('blanks a <sup> marker to spaces, preserving textContent length', () => {
		const el = block('true religion.<sup>1</sup><sup>1</sup> More');
		const out = blankFootnoteMarkers(el);
		// Length must equal textContent exactly, or highlight/search offsets drift.
		expect(out.length).toBe(el.textContent!.length);
		expect(out).toBe('true religion.   More');
		// The digits are gone, so a search for "religion" or "More" still lands,
		// but one for "11" cannot match the marker.
		expect(out.toLowerCase().includes('11')).toBe(false);
	});

	it('blanks an inline [4] marker to spaces, preserving length', () => {
		const el = block('availeth much.[4] The way');
		const out = blankFootnoteMarkers(el);
		expect(out.length).toBe(el.textContent!.length);
		expect(out).toBe('availeth much.    The way');
	});

	it('leaves ordinary prose (and the editor’s bracket) untouched', () => {
		const el = block('he gave [him] grace');
		expect(blankFootnoteMarkers(el)).toBe('he gave [him] grace');
	});

	it('blanks aria-hidden decoration', () => {
		const el = block('word<span aria-hidden="true">✦</span> more');
		const out = blankFootnoteMarkers(el);
		expect(out.length).toBe(el.textContent!.length);
		expect(out).toBe('word  more');
	});
});
