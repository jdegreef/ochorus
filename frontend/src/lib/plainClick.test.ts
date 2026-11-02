import { describe, expect, it } from 'vitest';
import { isPlainPrimaryClick, isUnmodifiedPrimaryClick } from './plainClick';

const click = (over: Partial<MouseEvent> = {}) => ({
	button: 0,
	metaKey: false,
	ctrlKey: false,
	shiftKey: false,
	altKey: false,
	defaultPrevented: false,
	...over
});

const SPOILERS: Partial<MouseEvent>[] = [
	{ metaKey: true },
	{ ctrlKey: true },
	{ shiftKey: true },
	{ altKey: true },
	{ button: 1 },
	{ button: 2 }
];

describe('isUnmodifiedPrimaryClick', () => {
	it('accepts a plain primary click', () => {
		expect(isUnmodifiedPrimaryClick(click())).toBe(true);
	});
	it.each(SPOILERS)('rejects %o', (over) => {
		expect(isUnmodifiedPrimaryClick(click(over))).toBe(false);
	});
	it('ignores defaultPrevented (a caller that cares uses isPlainPrimaryClick)', () => {
		expect(isUnmodifiedPrimaryClick(click({ defaultPrevented: true }))).toBe(true);
	});
});

describe('isPlainPrimaryClick', () => {
	it('accepts a plain primary click', () => {
		expect(isPlainPrimaryClick(click())).toBe(true);
	});
	it.each([...SPOILERS, { defaultPrevented: true }])('rejects %o', (over) => {
		expect(isPlainPrimaryClick(click(over))).toBe(false);
	});
	it('reads a real MouseEvent', () => {
		expect(isPlainPrimaryClick(new MouseEvent('click', { button: 0 }))).toBe(true);
		expect(isPlainPrimaryClick(new MouseEvent('click', { ctrlKey: true }))).toBe(false);
		const claimed = new MouseEvent('click', { cancelable: true });
		claimed.preventDefault();
		expect(isPlainPrimaryClick(claimed)).toBe(false);
	});
});
