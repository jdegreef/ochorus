import { beforeEach, describe, expect, it } from 'vitest';
import { sermonMarks } from './sermonMarks.svelte';

beforeEach(() => localStorage.clear());

describe('sermonMarks store', () => {
	it('adds a selection as one group, toggles and removes it', () => {
		sermonMarks.load('faith');
		const id = sermonMarks.add([
			{ p: 0, s: 0, e: 5 },
			{ p: 1, s: 0, e: 3 }
		]);
		expect(id).toBeTruthy();
		expect(sermonMarks.list).toHaveLength(2);
		expect(sermonMarks.groupCovering([{ p: 0, s: 0, e: 5 }, { p: 1, s: 0, e: 3 }])).toBe(id);

		sermonMarks.remove(id);
		expect(sermonMarks.list).toHaveLength(0);
	});

	it('keeps a note on the first segment and reads it back', () => {
		sermonMarks.load('faith');
		const id = sermonMarks.add([{ p: 2, s: 1, e: 4 }], 'a thought');
		expect(sermonMarks.getNote(id)).toBe('a thought');
		sermonMarks.setNote(id, 'revised');
		expect(sermonMarks.getNote(id)).toBe('revised');
	});

	it('stores a highlight colour and recolours a group', () => {
		sermonMarks.load('faith');
		const id = sermonMarks.add([{ p: 0, s: 0, e: 5 }], undefined, 'blue');
		expect(sermonMarks.getColor(id)).toBe('blue');
		sermonMarks.setColor(id, 'green');
		expect(sermonMarks.getColor(id)).toBe('green');
		// The default clears the stored key — getColor falls back to gold.
		sermonMarks.setColor(id, 'gold');
		expect(sermonMarks.getColor(id)).toBe('gold');
		expect(sermonMarks.list.every((m) => m.color === undefined)).toBe(true);
	});

	it('defaults to gold when no colour was set', () => {
		sermonMarks.load('faith');
		const id = sermonMarks.add([{ p: 1, s: 0, e: 3 }]);
		expect(sermonMarks.getColor(id)).toBe('gold');
	});

	it('scopes marks per sermon slug and persists across loads', () => {
		sermonMarks.load('a');
		sermonMarks.add([{ p: 0, s: 0, e: 2 }]);
		sermonMarks.load('b');
		expect(sermonMarks.list).toHaveLength(0); // b has none
		sermonMarks.load('a');
		expect(sermonMarks.list).toHaveLength(1); // a's mark survived
	});

	it('all() lists every sermon that has marks', () => {
		sermonMarks.load('a');
		sermonMarks.add([{ p: 0, s: 0, e: 2 }]);
		sermonMarks.load('b');
		sermonMarks.add([{ p: 1, s: 0, e: 2 }]);
		expect(new Set(sermonMarks.all().map((s) => s.slug))).toEqual(new Set(['a', 'b']));
	});
});
