import { describe, expect, it } from 'vitest';
import { escapeHtml, markSnippet, highlightAround } from './highlight';

describe('escapeHtml', () => {
	it('escapes the HTML-significant characters', () => {
		expect(escapeHtml('a <b> & c')).toBe('a &lt;b&gt; &amp; c');
	});
});

describe('markSnippet', () => {
	it('turns full-text markers into <mark> spans', () => {
		expect(markSnippet('the ⟦prayer⟧ of faith')).toBe('the <mark>prayer</mark> of faith');
	});

	it('escapes injected HTML before inserting marks', () => {
		expect(markSnippet('<script>⟦x⟧')).toBe('&lt;script&gt;<mark>x</mark>');
	});
});

describe('highlightAround', () => {
	it('wraps the first case-insensitive match', () => {
		expect(highlightAround('The Prayer of faith', 'prayer')).toContain('<mark>Prayer</mark>');
	});

	it('windows a long paragraph around the match with ellipses', () => {
		const text = 'x'.repeat(200) + ' needle ' + 'y'.repeat(200);
		const out = highlightAround(text, 'needle', 20);
		expect(out).toContain('<mark>needle</mark>');
		expect(out.startsWith('… ')).toBe(true);
		expect(out.endsWith(' …')).toBe(true);
		expect(out.length).toBeLessThan(text.length);
	});

	it('falls back to the head of the text when the query is absent', () => {
		expect(highlightAround('no match here', 'zzz')).toBe('no match here');
		expect(highlightAround('no match here', 'zzz')).not.toContain('<mark>');
	});

	it('escapes HTML in the surrounding text', () => {
		expect(highlightAround('a <i> needle', 'needle')).toContain('a &lt;i&gt; ');
	});
});
