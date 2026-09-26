import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Page mode must paginate the chapter's ENDING, not hide it.
 *
 * Page mode — the default on a wide screen — hides every child of the article
 * except the pager. The plan strip and the whole end of the chapter (the plan
 * reflection, "Mark day done", the scripture chips, Previous/Next, "Next in
 * series", the colophon) sat outside the pager, so on desktop a plan reader
 * could not mark a day done and the last page of a book led nowhere.
 *
 * Source-shape checks, like readerChrome.test.ts: they cannot see a layout,
 * but they fail when the invariant is undone by someone who does not know why
 * the markup is nested the way it is.
 */

const SRC = join(import.meta.dirname, '..');
const READER = readFileSync(join(SRC, 'routes/books/[slug]/[order]/+page.svelte'), 'utf8');

/** The markup between the pager's opening tag and </article>. */
function pagerMarkup(): string {
	const start = READER.indexOf('<div class="pager"');
	const end = READER.search(/^<\/article>/m);
	expect(start, 'the pager element must exist').toBeGreaterThan(-1);
	return READER.slice(start, end);
}

describe('the chapter ending lives inside the pager', () => {
	it('puts the plan strip, chapter nav and colophon inside the pager', () => {
		const pager = pagerMarkup();
		expect(pager, 'Mark day done must be reachable in page mode').toContain('completePlanDay');
		expect(pager, 'the chapter-end block must be paginated').toContain('class="chapter-end"');
		expect(pager, 'Next / Next in series must be paginated').toContain('book.seriesNext');
		expect(pager, 'the colophon must be paginated').toContain('authorPath(chapter.author_slug)');
	});

	it('leaves only the breadcrumb between <article> and the pager', () => {
		const open = READER.search(/^<article\b/m);
		expect(open, 'the article element must exist').toBeGreaterThan(-1);
		const between = READER.slice(open, READER.indexOf('<div class="pager"'));
		expect(between).toContain('<Breadcrumb');
		expect(between, 'anything here is hidden in page mode').not.toMatch(/<(nav|section|button)\b/);
	});

	it('hides the non-pager children with a selector that reaches child components', () => {
		// A scoped `:not(.pager)` only matches elements carrying this component's
		// class, so it never hid <Breadcrumb>, which then pushed the full-height
		// pager down and sliced the last line of every page.
		expect(READER).toMatch(/article\.paged > :global\(:not\(\.pager\)\)/);
	});
});
