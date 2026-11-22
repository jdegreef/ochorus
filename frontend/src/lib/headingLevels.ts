/**
 * Make a body's headings continue the page's outline.
 *
 * The page title is the `<h1>`, so a body's top heading level should be 2.
 * Many imported chapters open at `<h3>` or `<h4>` (6,000+ and 1,400+ chapters
 * in the fixture), so a screen reader's heading list jumped from level 1 to 3
 * (axe `heading-order`; bug review 2026-11-22, #33). The tags stay as they are,
 * because `.reading h2` and `.reading h3` are styled differently and the type
 * must not change; each heading instead gets an `aria-level` shifted so the top
 * one is 2. A body that already starts at 2 (or has no headings) is returned
 * unchanged.
 */
const HEADING = /<h([1-6])(?=[\s>])([^>]*)>/gi;

export function alignHeadingLevels(html: string): string {
	let top = 7;
	for (const m of html.matchAll(HEADING)) top = Math.min(top, Number(m[1]));
	if (top > 6 || top <= 2) return html;
	const shift = top - 2;
	return html.replace(HEADING, (whole, level: string, attrs: string) =>
		/\baria-level=/i.test(attrs)
			? whole
			: `<h${level}${attrs} aria-level="${Number(level) - shift}">`
	);
}
