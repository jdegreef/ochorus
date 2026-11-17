import { describe, expect, it } from 'vitest';
import { anchorParagraphs, paragraphFromHash, paragraphUrl } from './paragraphAnchor';

describe('anchorParagraphs', () => {
	it('numbers top-level elements the way Element.children does', () => {
		const html =
			'<h2>One</h2>\n<p>Two <em>nested</em> <a href="#x">link</a></p>\ntext<blockquote><p>Three</p></blockquote>';
		expect(anchorParagraphs(html)).toBe(
			'<h2 id="p-0">One</h2>\n<p id="p-1">Two <em>nested</em> <a href="#x">link</a></p>\ntext<blockquote id="p-2"><p>Three</p></blockquote>'
		);
		const doc = document.createElement('div');
		doc.innerHTML = anchorParagraphs(html);
		[...doc.children].forEach((el, i) => expect(el.id).toBe(`p-${i}`));
	});

	it('counts void and self-closed elements without nesting into them', () => {
		expect(anchorParagraphs('<hr><p>a<br>b</p><img src="x" />')).toBe(
			'<hr id="p-0"><p id="p-1">a<br>b</p><img id="p-2" src="x" />'
		);
	});

	it('keeps an existing id but still counts the element', () => {
		expect(anchorParagraphs('<p id="fn1">a</p><p>b</p>')).toBe(
			'<p id="fn1">a</p><p id="p-1">b</p>'
		);
	});

	it('ignores tags in comments, attribute values and raw text', () => {
		expect(
			anchorParagraphs('<!-- <p> --><p title="a > b">x</p><script>"<p>"</script><p>y</p>')
		).toBe(
			'<!-- <p> --><p id="p-0" title="a > b">x</p><script id="p-1">"<p>"</script><p id="p-2">y</p>'
		);
	});
});

describe('paragraph links', () => {
	it('reads only a #p-N fragment', () => {
		expect(paragraphFromHash('#p-12')).toBe(12);
		expect(paragraphFromHash('#p-')).toBeNull();
		expect(paragraphFromHash('#top')).toBeNull();
		expect(paragraphFromHash('')).toBeNull();
	});

	it('points the page URL at one paragraph', () => {
		expect(paragraphUrl('https://ochorus.com/books/x/3/?p=4&q=grace#p-4', 9)).toBe(
			'https://ochorus.com/books/x/3/?q=grace#p-9'
		);
		expect(paragraphUrl('https://ochorus.com/sermons/y/', undefined)).toBe(
			'https://ochorus.com/sermons/y/'
		);
	});
});
