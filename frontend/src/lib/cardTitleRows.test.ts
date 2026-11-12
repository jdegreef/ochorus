/**
 * One rule for a cover card's title (page-design Q4): it reserves two lines
 * (`min-h-[2lh]`), so the author line under it sits level across a row
 * whether the title wraps or not. A card that let a one-line title pull its
 * author up beside a two-line neighbour mixed the two rules on one shelf.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (p: string) => readFileSync(join(process.cwd(), 'src', p), 'utf-8');

// Cover cards that set a clamped title over an author line.
const CARDS = [
	'lib/components/BookCard.svelte',
	'lib/components/ShelfBook.svelte',
	'lib/components/ArticleShelf.svelte',
	'routes/articles/+page.svelte'
];

describe('cover card titles', () => {
	it.each(CARDS)('%s reserves two lines for the title', (file) => {
		const src = read(file);
		const clamps = [...src.matchAll(/class="[^"]*\bline-clamp-2\b[^"]*\bfont-medium\b[^"]*"/g)].map((m) => m[0]);
		expect(clamps.length, 'a clamped title').toBeGreaterThan(0);
		for (const c of clamps) expect(c).toMatch(/\bmin-h-\[2lh\]/);
	});
});
