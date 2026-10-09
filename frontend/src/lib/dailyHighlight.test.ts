import { describe, expect, it } from 'vitest';
import { dailyHighlight } from './dailyHighlight';
import { workKey, type MarksStore } from './reading-schema';

const long = (s: string) => `${s} — a passage long enough to be worth meeting again.`;

describe('dailyHighlight', () => {
	const store: MarksStore = {
		[workKey('book', 'humility', 3)]: {
			m: [
				{ id: 'b', p: 0, s: 0, e: 10, q: long('Humility is the displacement of self') },
				// The same group's second paragraph: counted once.
				{ id: 'b', p: 1, s: 0, e: 10, q: long('continued') },
				{ id: 'x', p: 2, s: 0, e: 4, q: 'Amen' }
			]
		},
		[workKey('sermon', 'the-prayer', 1)]: {
			m: [{ id: 'a', p: 0, s: 0, e: 10, q: long('Pray without ceasing'), note: 'Mine' }]
		},
		[workKey('book', 'old', 1)]: { m: [{ id: 'c', p: 0, s: 0, e: 10 }] }
	};

	it('turns over day by day through the passages, stable for a day', () => {
		const a = dailyHighlight(100, store)!;
		const b = dailyHighlight(101, store)!;
		expect(a.text).not.toBe(b.text);
		expect(dailyHighlight(102, store)).toEqual(a);
		expect(dailyHighlight(100, store)).toEqual(a);
	});

	it('says where the passage is, with the reader’s note', () => {
		const picks = [0, 1].map((d) => dailyHighlight(d, store)!);
		expect(picks).toContainEqual({ kind: 'sermon', slug: 'the-prayer', order: 1, text: long('Pray without ceasing'), note: 'Mine' });
		expect(picks.map((p) => p.slug)).toContain('humility');
	});

	it('skips marks with no stored quote, or too short to be a passage', () => {
		const texts = [0, 1, 2, 3].map((d) => dailyHighlight(d, store)!.text);
		expect(texts).not.toContain('Amen');
		expect(texts.every((t) => t.length >= 40)).toBe(true);
	});

	it('is null with nothing to show', () => {
		expect(dailyHighlight(1, {})).toBeNull();
	});
});
