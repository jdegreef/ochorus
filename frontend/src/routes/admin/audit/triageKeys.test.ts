import { describe, expect, it } from 'vitest';
import { isTypingTarget, stepIndex, triageAction } from './triageKeys';

const el = (html: string) => {
	const host = document.createElement('div');
	host.innerHTML = html;
	return host.firstElementChild as HTMLElement;
};

describe('triageAction', () => {
	const row = el('<li tabindex="-1"></li>');

	it('maps the triage keys on a finding row', () => {
		expect(triageAction({ key: 'j', target: row })).toBe('next');
		expect(triageAction({ key: 'k', target: row })).toBe('prev');
		expect(triageAction({ key: 'a', target: row })).toBe('accept');
		expect(triageAction({ key: 'o', target: row })).toBe('open');
		expect(triageAction({ key: 'Enter', target: row })).toBe('toggle');
		expect(triageAction({ key: ' ', target: row })).toBe('toggle');
		expect(triageAction({ key: 'x', target: row })).toBeNull();
		expect(triageAction({ key: 'J', target: row })).toBeNull();
	});

	it('works with nothing focused', () => {
		expect(triageAction({ key: 'j', target: document.body })).toBe('next');
		expect(triageAction({ key: 'j', target: null })).toBe('next');
	});

	it('leaves modified keys to the browser', () => {
		expect(triageAction({ key: 'a', target: row, metaKey: true })).toBeNull();
		expect(triageAction({ key: 'o', target: row, ctrlKey: true })).toBeNull();
		expect(triageAction({ key: 'j', target: row, altKey: true })).toBeNull();
	});

	it('ignores keys while typing', () => {
		for (const html of ['<input />', '<textarea></textarea>', '<select></select>']) {
			expect(triageAction({ key: 'j', target: el(html) })).toBeNull();
			expect(triageAction({ key: 'a', target: el(html) })).toBeNull();
		}
	});

	it("keeps a control's own Enter / Space but still moves from it", () => {
		for (const html of ['<a href="/x">x</a>', '<button>b</button>', '<summary>s</summary>']) {
			const t = el(html);
			expect(triageAction({ key: 'Enter', target: t })).toBeNull();
			expect(triageAction({ key: ' ', target: t })).toBeNull();
			expect(triageAction({ key: 'j', target: t })).toBe('next');
		}
	});
});

describe('isTypingTarget', () => {
	it('treats contenteditable as typing', () => {
		const div = el('<div contenteditable="true"></div>');
		// jsdom doesn't compute isContentEditable; stand in for the browser.
		Object.defineProperty(div, 'isContentEditable', { value: true });
		expect(isTypingTarget(div)).toBe(true);
		expect(isTypingTarget(el('<li></li>'))).toBe(false);
		expect(isTypingTarget(null)).toBe(false);
	});
});

describe('stepIndex', () => {
	it('enters at either end from nothing focused', () => {
		expect(stepIndex(-1, 1, 5)).toBe(0);
		expect(stepIndex(-1, -1, 5)).toBe(4);
	});
	it('moves and clamps', () => {
		expect(stepIndex(2, 1, 5)).toBe(3);
		expect(stepIndex(2, -1, 5)).toBe(1);
		expect(stepIndex(4, 1, 5)).toBe(4);
		expect(stepIndex(0, -1, 5)).toBe(0);
	});
	it('handles an empty list and a stale index', () => {
		expect(stepIndex(0, 1, 0)).toBe(-1);
		expect(stepIndex(9, 1, 3)).toBe(0);
	});
});
