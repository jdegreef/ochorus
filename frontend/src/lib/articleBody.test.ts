import { describe, expect, it } from 'vitest';
import { splitBeforeSection } from './articleBody';

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
