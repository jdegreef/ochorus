import { afterEach, describe, expect, it, vi } from 'vitest';
import { focusTrap } from './focusTrap';

// jsdom does no layout, so offsetParent is null for everything — mark elements
// "visible" the way a real browser would so the action's visibility filter works.
function visible<T extends HTMLElement>(el: T): T {
	Object.defineProperty(el, 'offsetParent', { get: () => document.body, configurable: true });
	return el;
}

function setup() {
	document.body.innerHTML = '';
	const opener = visible(document.createElement('button'));
	opener.textContent = 'open';
	document.body.append(opener);
	opener.focus();

	const panel = document.createElement('div');
	const a = visible(document.createElement('button'));
	const b = visible(document.createElement('button'));
	a.textContent = 'first';
	b.textContent = 'last';
	panel.append(a, b);
	document.body.append(panel);
	return { opener, panel, a, b };
}

afterEach(() => vi.restoreAllMocks());

describe('focusTrap action', () => {
	it('moves focus into the panel on mount', async () => {
		const { panel, a } = setup();
		focusTrap(panel);
		await Promise.resolve(); // let the queueMicrotask focus run
		expect(document.activeElement).toBe(a);
	});

	it('calls onEscape when Escape is pressed inside the panel', () => {
		const { panel, a } = setup();
		const onEscape = vi.fn();
		focusTrap(panel, { onEscape });
		a.focus();
		a.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
		expect(onEscape).toHaveBeenCalledOnce();
	});

	it('wraps Tab from the last focusable back to the first', () => {
		const { panel, a, b } = setup();
		focusTrap(panel, { autoFocus: false });
		b.focus();
		const ev = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });
		b.dispatchEvent(ev);
		expect(document.activeElement).toBe(a);
		expect(ev.defaultPrevented).toBe(true);
	});

	it('wraps Shift+Tab from the first focusable back to the last', () => {
		const { panel, a, b } = setup();
		focusTrap(panel, { autoFocus: false });
		a.focus();
		a.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true }));
		expect(document.activeElement).toBe(b);
	});

	it('returns focus to the opener when destroyed', () => {
		const { opener, panel } = setup();
		const trap = focusTrap(panel, { autoFocus: false });
		panel.querySelector('button')!.focus();
		trap.destroy();
		expect(document.activeElement).toBe(opener);
	});
});
