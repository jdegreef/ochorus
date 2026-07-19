import { describe, expect, it } from 'vitest';
import { pointLabel } from './sermonOutline';

describe('sermon outline — pointLabel', () => {
	it('lifts the ALL-CAPS thesis of a homiletic point', () => {
		expect(pointLabel('I. First, we have here A GOSPEL REJECTED. One would…')).toBe(
			'I. A Gospel Rejected'
		);
		expect(pointLabel('II. Let us now take the second head—AN ANSWER PROMISED. We…')).toBe(
			'II. An Answer Promised'
		);
		expect(pointLabel('I. The first head is PRAYER COMMANDED. We are not…')).toBe(
			'I. Prayer Commanded'
		);
	});

	it('falls back to the leading words when there is no caps run', () => {
		const out = pointLabel('III. Now consider the comfort this doctrine brings to us daily.');
		expect(out).toMatch(/^III\. Now Consider The Comfort/);
	});

	it('ignores paragraphs that are not points', () => {
		expect(pointLabel('This is ordinary prose about prayer.')).toBeNull();
		expect(pointLabel('In 1 Corinthians 2:2 Paul writes…')).toBeNull();
		// A lone initial or mid-sentence roman numeral is not a point.
		expect(pointLabel('I am persuaded that nothing can separate us.')).toBeNull();
	});

	it('caps the label length', () => {
		const long = 'IV. ' + Array.from({ length: 20 }, (_, i) => `word${i}`).join(' ');
		expect(pointLabel(long)!.endsWith('…')).toBe(true);
	});
});
