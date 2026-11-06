import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * The book page must say something about the BOOK.
 *
 * Before #1236 it did not. `description` fed the meta tag and the JSON-LD and
 * was never rendered, while the AUTHOR's bio was — so a reader landing on a
 * fourth-century treatise met a chapter list and a paragraph about Athanasius,
 * and nothing about the work itself.
 *
 * Two things are guarded, and the second is the one that would rot quietly:
 *
 *  1. The long-form `about_html` is rendered. Ten works carry one today.
 *  2. It FALLS BACK to `description`. That branch is what puts prose on the
 *     other 162 editions, which have a description and no long-form piece.
 *     Delete it and 162 pages silently lose their only words about the work
 *     while the ten pilot pages keep theirs — nothing else in the suite, and
 *     nothing on the ten pages a reviewer would check, would notice.
 *
 * A source check rather than a render: the page needs a live API to render, and
 * what is being asserted is that the branch EXISTS, which the source shows.
 */

const PAGE = readFileSync(
	join(import.meta.dirname, '..', 'routes/books/[slug]/+page.svelte'),
	'utf8'
);

describe('the book page states what the book is', () => {
	it('renders the long-form about_html', () => {
		expect(PAGE).toMatch(/\{#if book\.about_html\}/);
		expect(PAGE).toMatch(/\{@html book\.about_html\}/);
	});

	it('falls back to description when there is no long-form piece', () => {
		expect(PAGE).toMatch(/\{:else if book\.description\}/);
	});

	it('heads both branches with the one translated label', () => {
		// Both branches sit inside one About section headed by `book.aboutWork`
		// (design review #9 folded them under a shared layout). Count the
		// HEADINGS, not every use of the key — the jump nav reuses the label.
		expect(PAGE.match(/<h2 id="about-work"[^>]*>\{t\('book\.aboutWork'\)\}/g)?.length).toBe(1);
		const section = PAGE.slice(PAGE.indexOf('{#if hasAbout}'), PAGE.indexOf('{:else if hasAboutFoot'));
		expect(section).toMatch(/\{#if book\.about_html\}/);
		expect(section).toMatch(/\{:else if book\.description\}/);
	});

	it('does not show the author bio', () => {
		// Dropped deliberately: it sat under "About this book" in muted type and
		// read as a second paragraph of the book's own prose — the author's dates
		// and career presented as if they were what the book is about. The byline
		// links to the author page, which is where that summary belongs.
		expect(PAGE).not.toMatch(/book\.author\.bio/);
	});

	it('holds the prose to a reading measure', () => {
		// Design review #9 reversed the old full-width band: at ~150 characters
		// a line the description was scanned, not read. Both branches render
		// inside `.about-prose`, which the page holds to ~65ch.
		const section = PAGE.slice(PAGE.indexOf('{#if hasAbout}'), PAGE.indexOf('{:else if hasAboutFoot'));
		expect(section.indexOf('<div class="about-prose">')).toBeLessThan(section.indexOf('{#if book.about_html}'));
		expect(PAGE).toMatch(/\.about-prose \{\s*max-width: 65ch;/);
	});
});
