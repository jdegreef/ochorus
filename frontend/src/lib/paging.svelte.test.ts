import { describe, expect, it } from 'vitest';
import { pager } from './paging.svelte';

const items = Array.from({ length: 60 }, (_, i) => i);

describe('pager', () => {
	it('shows a page, then a page more per tap, and says how many the next adds', () => {
		const p = pager(() => items, () => 'k', 24);
		expect(p.visible).toHaveLength(24);
		expect(p.next).toBe(24);
		p.more();
		expect(p.visible).toHaveLength(48);
		expect(p.next).toBe(12);
		p.more();
		expect(p.remaining).toBe(0);
	});

	it('starts over when the view key changes', () => {
		let key = $state('a');
		const p = pager(() => items, () => key, 24);
		p.more();
		expect(p.visible).toHaveLength(48);
		key = 'b';
		expect(p.visible).toHaveLength(24);
	});

	it('reveals the page holding an index, never shrinking', () => {
		const p = pager(() => items, () => 'k', 24);
		p.reveal(30);
		expect(p.visible).toHaveLength(48);
		p.reveal(3);
		expect(p.visible).toHaveLength(48);
	});

	it('restores a captured count only while its key still matches', () => {
		let key = $state('a');
		const first = pager(() => items, () => key, 24);
		first.more();
		const saved = first.capture();

		const again = pager(() => items, () => key, 24);
		again.restore(saved);
		expect(again.visible).toHaveLength(48);

		key = 'b';
		const other = pager(() => items, () => key, 24);
		other.restore(saved);
		expect(other.visible).toHaveLength(24);
		other.restore(undefined);
		expect(other.visible).toHaveLength(24);
	});

	it('opens on a separate first page, then pages by the batch', () => {
		const many = Array.from({ length: 160 }, (_, i) => i);
		const p = pager(() => many, () => 'k', 48, 56);
		expect(p.visible).toHaveLength(56);
		expect(p.next).toBe(48);
		p.more();
		expect(p.visible).toHaveLength(104);
		expect(p.next).toBe(48);
		p.more();
		expect(p.visible).toHaveLength(152);
		expect(p.next).toBe(8);
	});

	it('reveals past a separate first page in whole batches', () => {
		const many = Array.from({ length: 160 }, (_, i) => i);
		const p = pager(() => many, () => 'k', 48, 56);
		p.reveal(40);
		expect(p.visible).toHaveLength(56);
		p.reveal(56);
		expect(p.visible).toHaveLength(104);
		p.reveal(104);
		expect(p.visible).toHaveLength(152);
	});
});
