import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import BookListRow from './BookListRow.svelte';
import type { BookSummary } from '$lib/library';

/**
 * The row must show a whole title, on a phone as much as on a desk.
 *
 * At 390px the meta column ("36 chapters", "3 hr 7 min read") was taking a
 * third of the row, and the three text lines were each `truncate` — so the
 * shelf read "The Inner Cha…", "Baptism with …", "Frederick Brotherton M…".
 * A library's list of books is the one place the titles have to be legible.
 *
 * These assert the two halves of the fix: nothing clips the text, and the meta
 * gets out of the way below `sm` rather than competing for the same line. Read
 * from the source in the idiom `colorTokens.test.ts` and `rtl.test.ts` use —
 * jsdom applies no stylesheet, so `truncate` coming back would be invisible to
 * a rendered assertion.
 */
const source = readFileSync(join(process.cwd(), 'src/lib/components/BookListRow.svelte'), 'utf-8');

const book = (over: Partial<BookSummary> = {}): BookSummary =>
	({
		slug: 'the-inner-chamber',
		title: 'The Inner Chamber and the Inner Life',
		subtitle: 'And the Deepest Secret of Prayer',
		author: { slug: 'andrew-murray', name: 'Andrew Murray' },
		cover_url: '',
		cover_color: '#1864ab',
		chapter_count: 36,
		word_count: 42000,
		language: 'en',
		source_type: 'public_domain',
		...over
	}) as BookSummary;

let target: HTMLElement;
let component: Record<string, unknown> | undefined;

const render = (props: { book: BookSummary; showAuthor?: boolean }): HTMLElement => {
	teardown();
	target = document.createElement('div');
	document.body.appendChild(target);
	component = mount(BookListRow, { target, props }) as Record<string, unknown>;
	return target;
};

const teardown = () => {
	if (component) unmount(component);
	target?.remove();
	component = undefined;
};

afterEach(teardown);

describe('the book row shows the whole title', () => {
	it('renders title, author and subtitle in full', () => {
		const el = render({ book: book() });
		const text = el.textContent ?? '';
		expect(text).toContain('The Inner Chamber and the Inner Life');
		expect(text).toContain('Andrew Murray');
		expect(text).toContain('And the Deepest Secret of Prayer');
		// No ellipsis of our own making — CSS clipping is caught below.
		expect(text).not.toContain('…');
	});

	it('still carries the chapter count and reading time', () => {
		const text = render({ book: book() }).textContent ?? '';
		expect(text).toContain('36');
		expect(text).toMatch(/\d+\s*(hr|min)/);
	});
});

describe('nothing in the row clips its text', () => {
	it('applies no truncate or line-clamp to the title, author or subtitle', () => {
		const offending = source
			.split('\n')
			.filter((line) => /\{book\.(title|subtitle)\}|\{book\.author\.name\}/.test(line))
			.filter((line) => /\btruncate\b|\bline-clamp-/.test(line));
		expect(offending).toEqual([]);
	});

	it('drops the meta column onto its own line below sm, so the title has the width', () => {
		// `w-full … sm:w-auto` on the meta block is what frees the row; without it
		// the title is back to sharing 390px with "3 hr 43 min read".
		expect(source).toMatch(/w-full[^"]*sm:w-auto/);
		// Logical padding, so the indent flips in Arabic (frontend/CLAUDE.md).
		expect(source).toMatch(/\bps-16\b/);
		expect(source).not.toMatch(/\bpl-16\b/);
	});
});
