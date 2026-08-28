import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * A chapter can have no name.
 *
 * Bounds's *Purpose in Prayer* is thirteen untitled chapters — the source gives
 * them no heading, only an epigraph — so they ship with `title: ''` rather than
 * a synthetic "Chapter 1" that the reader would then render as "1. Chapter 1".
 *
 * That makes the empty-title branch real for the first time, and the fallback
 * that was already there was wrong for a book: `plans.day` is the READING PLAN
 * label, so an untitled chapter read "1. Day 1".
 *
 * Read from source rather than rendered: all three call sites sit inside `{#each}`
 * blocks over data these tests would otherwise have to reconstruct wholesale, and
 * what is being asserted is which label the branch reaches for — a fact of the
 * markup, not of the layout. Same idiom as `BookListRow.test.ts`.
 */
const read = (p: string) => readFileSync(join(process.cwd(), p), 'utf-8');

const SITES = [
	['TOC drawer', 'src/lib/components/TocDrawer.svelte', 'ch'],
	['search drawer', 'src/lib/components/SearchDrawer.svelte', 'hit'],
	['notebook', 'src/routes/notebook/+page.svelte', 'ch'],
] as const;

describe('a chapter with no title', () => {
	it.each(SITES)('%s labels it "Chapter N", not "Day N"', (_name, path, item) => {
		const source = read(path);
		expect(source).toContain(
			`${item}.title ? \`\${${item}.order}. \${${item}.title}\` : ` +
				`\`\${t('settings.chapterN')} \${${item}.order}\``
		);
	});

	it('never falls back to the reading-plan label in the book TOC', () => {
		// The bug this replaced: `ch.title || `${t('plans.day')} ${ch.order}`` in a
		// drawer that only ever lists a BOOK's chapters.
		expect(read('src/lib/components/TocDrawer.svelte')).not.toContain("t('plans.day')");
	});

	it('keeps the number out of the fallback, so it cannot double up', () => {
		// "1. Chapter 1" is the whole thing we are avoiding: the fallback carries
		// the number itself and must NOT be prefixed with the order as well.
		for (const [, path, item] of SITES) {
			expect(read(path)).not.toContain(
				`{${item}.order}. {${item}.title || \`\${t('settings.chapterN')}`
			);
		}
	});
});
