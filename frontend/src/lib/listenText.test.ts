import { describe, it, expect } from 'vitest';
import { spokenText } from './listenText';

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
