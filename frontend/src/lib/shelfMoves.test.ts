import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./readingSync', () => ({
	readingSync: {
		pushProgress: () => {},
		pushActivity: () => {},
		setFinished: () => {},
		removeProgress: () => {},
		pushFavorite: () => {},
		pushShelf: () => {}
	}
}));

import { moveBetweenShelves, moveToToRead } from './shelfMoves';
import { customShelves } from './customShelves.svelte';
import { favorites } from './favorites.svelte';
import { getProgressRecord, markFinished, saveProgress } from './progress';
import { undo } from './undo.svelte';

beforeEach(() => {
	localStorage.clear();
	undo.dismiss();
});

describe('moveToToRead', () => {
	it('drops the position and hearts the book; Undo restores both', () => {
		saveProgress('humility', 4, 'en');
		markFinished('humility');
		expect(moveToToRead('humility')).toBe(true);
		expect(getProgressRecord('humility')).toBeNull();
		expect(favorites.has('book', 'humility')).toBe(true);
		expect(undo.current?.kind).toBe('moved');
		undo.act();
		expect(getProgressRecord('humility')).toMatchObject({ order: 4 });
		expect(getProgressRecord('humility')?.finished_at).toBeTypeOf('number');
		expect(favorites.has('book', 'humility')).toBe(false);
	});

	it('leaves an existing heart alone on Undo', () => {
		saveProgress('humility', 2, 'en');
		favorites.toggle('book', 'humility');
		moveToToRead('humility');
		undo.act();
		expect(favorites.has('book', 'humility')).toBe(true);
	});

	it('does nothing for a book with no position', () => {
		expect(moveToToRead('never-opened')).toBe(false);
		expect(favorites.has('book', 'never-opened')).toBe(false);
		expect(undo.current).toBeNull();
	});
});

describe('moveBetweenShelves', () => {
	it('moves a book and Undo puts it back', () => {
		const a = customShelves.create('Lent', 'humility')!;
		const b = customShelves.create('Group')!;
		moveBetweenShelves(a, b, 'humility');
		expect(customShelves.has(a, 'humility')).toBe(false);
		expect(customShelves.has(b, 'humility')).toBe(true);
		undo.act();
		expect(customShelves.has(a, 'humility')).toBe(true);
		expect(customShelves.has(b, 'humility')).toBe(false);
	});

	it('onto a shelf that already holds it: just leaves the first, and Undo keeps the second', () => {
		const a = customShelves.create('Lent', 'humility')!;
		const b = customShelves.create('Group', 'humility')!;
		moveBetweenShelves(a, b, 'humility');
		expect(customShelves.has(a, 'humility')).toBe(false);
		undo.act();
		expect(customShelves.has(a, 'humility')).toBe(true);
		expect(customShelves.has(b, 'humility')).toBe(true);
	});
});
