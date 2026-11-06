// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { foldBio, FOLD_ATTR } from './bioFold';

const P = (n: number) => `<p>Para ${n}.</p>`;

describe('foldBio', () => {
	it('marks the first element after three top-level paragraphs', () => {
		const html = [P(1), '<h2>A</h2>', P(2), P(3), '<blockquote><p>Q</p></blockquote>', P(4), P(5)].join('\n');
		const { html: out, folded } = foldBio(html);
		expect(folded).toBe(true);
		expect(out).toContain(`<blockquote ${FOLD_ATTR}>`);
		// Nothing else changed: the Reader's paragraph indices still line up.
		expect(out.replace(` ${FOLD_ATTR}`, '')).toBe(html);
	});

	it('counts only top-level paragraphs, not those inside a quote or callout', () => {
		const html = [P(1), '<div class="prayer"><p>a</p><p>b</p></div>', P(2), P(3), P(4), P(5)].join('');
		expect(foldBio(html).html).toContain(`<p ${FOLD_ATTR}>Para 4.`);
	});

	it('never leaves a heading stranded at the end of the opening', () => {
		const html = [P(1), P(2), P(3), '<h2>Next</h2>', P(4), P(5)].join('');
		// The fold already sits before the heading; a heading as the last shown
		// element moves the fold up past it.
		expect(foldBio(html).html).toContain(`<h2 ${FOLD_ATTR}>`);
		const stranded = [P(1), P(2), '<h2>B</h2>', P(3), '<h2>C</h2>', P(4), P(5)].join('');
		expect(foldBio(stranded).html).toContain(`<h2 ${FOLD_ATTR}>C`);
	});

	it('does not fold a short life', () => {
		const html = [P(1), P(2), P(3), P(4)].join('');
		expect(foldBio(html)).toEqual({ html, folded: false });
		expect(foldBio(P(1)).folded).toBe(false);
		expect(foldBio('').folded).toBe(false);
	});

	it('steps over void and self-closing tags', () => {
		const html = [`<p>a<br>b</p>`, '<hr>', P(2), `<p><img src="x" /></p>`, P(4), P(5)].join('');
		expect(foldBio(html).html).toContain(`<p ${FOLD_ATTR}>Para 4.`);
	});
});
