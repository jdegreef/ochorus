import { describe, expect, it } from 'vitest';
import { scriptureRefs, splitBeforeSection } from './articleBody';

describe('splitBeforeSection', () => {
	const body = '<p>Intro.</p><h2 id="a">One</h2><p>x</p><h2 id="b">Two</h2><p>y</p>';

	it('cuts just before the nth <h2>, keeping both halves whole', () => {
		expect(splitBeforeSection(body, 2)).toEqual([
			'<p>Intro.</p><h2 id="a">One</h2><p>x</p>',
			'<h2 id="b">Two</h2><p>y</p>'
		]);
		const [a, b] = splitBeforeSection(body, 1)!;
		expect(a + b).toBe(body);
		expect(b.startsWith('<h2 id="a">')).toBe(true);
	});

	it('is null when the body has too few sections, or opens on the section', () => {
		expect(splitBeforeSection(body, 3)).toBeNull();
		expect(splitBeforeSection('<p>No sections.</p>', 1)).toBeNull();
		expect(splitBeforeSection('<h2>First</h2><p>x</p>', 1)).toBeNull();
	});
});

describe('scriptureRefs', () => {
	it('lists each server-wrapped reference once, in order of first mention', () => {
		const html =
			'<p><a class="scripture-ref" data-ref="John 3:16">Jn 3:16</a> and ' +
			'<a class="scripture-ref" href="/scripture/romans/8/" data-ref="Romans 8:28">Rom 8:28</a>, ' +
			'again <a class="scripture-ref" data-ref="John 3:16">John 3:16</a>.</p>';
		expect(scriptureRefs(html)).toEqual(['John 3:16', 'Romans 8:28']);
	});

	it('ignores ordinary links and decodes entities', () => {
		expect(scriptureRefs('<a href="/books/x/">A book</a>')).toEqual([]);
		expect(scriptureRefs('<a class="scripture-ref" data-ref="Song of Songs 2:4 &amp; 8:6">x</a>')).toEqual([
			'Song of Songs 2:4 & 8:6'
		]);
	});
});
