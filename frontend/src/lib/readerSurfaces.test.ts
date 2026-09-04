import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * The three long-form reading surfaces must not offer controls they don't honour.
 *
 * Ochorus reads long prose in three places — book chapters, sermons and author
 * biographies — and all three mount <ReaderControls>. But paged (page-turn)
 * mode is implemented ONLY in the chapter reader: it needs a fixed viewport,
 * page measuring, turning and a scrubber, none of which lives in <Reader>,
 * which deliberately owns the prose rather than the container.
 *
 * So every surface was rendering a Scroll/Page switch, and on two of them it
 * did nothing — while still writing `readerPrefs.paged`, which is persisted, so
 * a reader who pressed "Page" on a sermon silently changed how their next
 * CHAPTER behaved. A control that appears to work and doesn't is worse than an
 * absent one.
 *
 * `layout` now defaults to false, so the safe failure is a hidden control
 * rather than a lying one. When paged mode becomes shared (design review items
 * 2-3), pass it everywhere and update this test to require it.
 */

const SRC = join(import.meta.dirname, '..');
const read = (f: string) => readFileSync(join(SRC, f), 'utf8');

/** Surfaces that mount <ReaderControls>, and whether they implement paged mode. */
const SURFACES: { label: string; file: string; paged: boolean }[] = [
	{ label: 'book chapter', file: 'routes/books/[slug]/[order]/+page.svelte', paged: true },
	{ label: 'sermon', file: 'routes/sermons/[slug]/+page.svelte', paged: false },
	{ label: 'author biography', file: 'routes/authors/[slug]/+page.svelte', paged: false },
	{ label: 'article', file: 'routes/articles/[slug]/+page.svelte', paged: false }
];

describe('reading surfaces only offer the layout switch where it works', () => {
	it.each(SURFACES.filter((s) => s.paged))(
		'$label implements paged mode AND offers the switch',
		({ file }) => {
			const src = read(file);
			expect(src, `${file}: should read readerPrefs.paged`).toMatch(/readerPrefs\.paged/);
			expect(src, `${file}: should pass \`layout\` to <ReaderControls>`).toMatch(
				/<ReaderControls[^>]*\blayout\b/
			);
		}
	);

	it.each(SURFACES.filter((s) => !s.paged))(
		'$label does NOT offer a switch it cannot honour',
		({ file }) => {
			const src = read(file);
			// If a surface ever starts honouring `paged`, this flips — and the
			// fix is to pass `layout` and move it to the list above, not to
			// delete the assertion.
			expect(src, `${file}: does not implement paged mode`).not.toMatch(/readerPrefs\.paged/);
			expect(src, `${file}: must not pass \`layout\``).not.toMatch(
				/<ReaderControls[^>]*\blayout\b/
			);
		}
	);

	it('ReaderControls hides the switch by default', () => {
		const src = read('lib/components/ReaderControls.svelte');
		expect(src, 'the `layout` prop should default to false').toMatch(/layout = false/);
		expect(src, 'the layout block should be guarded by {#if layout}').toMatch(/\{#if layout\}/);
	});
});

/**
 * Same rule for the Margins group. Only the chapter reader's article consumes
 * `--reading-margin` (its `.reading-article` padding); on a sermon or biography
 * the control would persist a pref and change nothing. And page mode zeroes the
 * article padding, so the group must also hide there.
 */
describe('reading surfaces only offer the Margins group where it works', () => {
	it('the chapter reader consumes --reading-margin AND passes `margins`', () => {
		const src = read('routes/books/[slug]/[order]/+page.svelte');
		expect(src, 'should consume --reading-margin').toMatch(/var\(--reading-margin/);
		expect(src, 'should pass `margins` to <ReaderControls>').toMatch(
			/<ReaderControls[^>]*\bmargins\b/
		);
	});

	it.each(SURFACES.filter((s) => !s.paged))(
		'$label does NOT offer a Margins group it cannot honour',
		({ file }) => {
			const src = read(file);
			expect(src, `${file}: does not consume --reading-margin`).not.toMatch(/--reading-margin/);
			expect(src, `${file}: must not pass \`margins\``).not.toMatch(
				/<ReaderControls[^>]*\bmargins\b/
			);
		}
	);

	it('ReaderControls hides the Margins group by default and in page mode', () => {
		const src = read('lib/components/ReaderControls.svelte');
		expect(src, 'the `margins` prop should default to false').toMatch(/margins = false/);
		expect(src, 'the group should be guarded by margins && !paged').toMatch(
			/\{#if margins && !readerPrefs\.paged\}/
		);
	});
});
