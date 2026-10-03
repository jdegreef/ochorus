import { afterEach, describe, expect, it } from 'vitest';
import { menuShift } from './menuShift';

function button(left: number, width: number, dir = 'ltr') {
	const el = document.createElement('button');
	el.dir = dir;
	el.style.direction = dir;
	document.body.appendChild(el);
	el.getBoundingClientRect = () =>
		({ left, right: left + width, top: 0, bottom: 30, width, height: 30 }) as DOMRect;
	return el;
}

function viewport(width: number) {
	Object.defineProperty(document.documentElement, 'clientWidth', { configurable: true, value: width });
}

afterEach(() => {
	document.body.innerHTML = '';
});

describe('menuShift', () => {
	it('hangs from the start edge when there is room', () => {
		viewport(1200);
		expect(menuShift(button(100, 80), 288)).toEqual({ width: 288, shift: 0 });
	});

	it('hangs from the end edge when asked', () => {
		viewport(1200);
		// right edge 180 → left 180 - 288 = -108 relative to the button
		expect(menuShift(button(400, 80), 288, 'end')).toEqual({ width: 288, shift: -208 });
	});

	it('slides an end-hung menu back inside a phone screen', () => {
		viewport(360);
		// Mid-row button: hung from its end edge the menu would start at -48.
		const { width, shift } = menuShift(button(150, 90), 288, 'end');
		expect(width).toBe(288);
		expect(150 + shift).toBe(8);
	});

	it('slides a start-hung menu back off the end edge', () => {
		viewport(360);
		const { shift } = menuShift(button(300, 40), 192);
		expect(300 + shift + 192).toBe(352);
	});

	it('never grows wider than the screen less the gutters', () => {
		viewport(280);
		const { width, shift } = menuShift(button(100, 40), 288);
		expect(width).toBe(264);
		expect(100 + shift).toBe(8);
	});

	it('mirrors start/end in RTL', () => {
		viewport(1200);
		expect(menuShift(button(400, 80, 'rtl'), 288).shift).toBe(80 - 288);
		expect(menuShift(button(400, 80, 'rtl'), 288, 'end').shift).toBe(0);
	});
});
