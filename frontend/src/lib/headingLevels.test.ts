import { describe, expect, it } from 'vitest';
import { alignHeadingLevels } from './headingLevels';

describe('alignHeadingLevels', () => {
	it('shifts a body that opens at h3 so its top heading is level 2', () => {
		expect(alignHeadingLevels('<h3>A</h3><p>x</p><h4>B</h4>')).toBe(
			'<h3 aria-level="2">A</h3><p>x</p><h4 aria-level="3">B</h4>'
		);
	});
	it('leaves a body that already starts at h2, or has no headings, alone', () => {
		expect(alignHeadingLevels('<h2>A</h2><h3>B</h3>')).toBe('<h2>A</h2><h3>B</h3>');
		expect(alignHeadingLevels('<p>hello</p>')).toBe('<p>hello</p>');
	});
	it('keeps attributes and an explicit aria-level, and ignores <header>', () => {
		expect(alignHeadingLevels('<h4 id="p-0">A</h4><header>h</header>')).toBe(
			'<h4 id="p-0" aria-level="2">A</h4><header>h</header>'
		);
		expect(alignHeadingLevels('<h3 aria-level="5">A</h3>')).toBe('<h3 aria-level="5">A</h3>');
	});
});
