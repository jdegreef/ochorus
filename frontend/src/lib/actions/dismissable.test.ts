import { describe, expect, it, vi } from 'vitest';
import { dismissable } from './dismissable';

function setup() {
	document.body.innerHTML = '';
	const root = document.createElement('div');
	const trigger = document.createElement('button');
	trigger.setAttribute('aria-expanded', 'true');
	const item = document.createElement('button');
	root.append(trigger, item);
	const outside = document.createElement('button');
	document.body.append(root, outside);
	return { root, trigger, item, outside };
}

const escape = () =>
	document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

describe('dismissable action', () => {
	it('dismisses on a click outside, not inside', () => {
		const { root, item, outside } = setup();
		const onDismiss = vi.fn();
		dismissable(root, { open: true, onDismiss });
		item.click();
		expect(onDismiss).not.toHaveBeenCalled();
		outside.click();
		expect(onDismiss).toHaveBeenCalledOnce();
	});

	it('treats a click on an item that detaches itself as inside', () => {
		const { root, item } = setup();
		const onDismiss = vi.fn();
		dismissable(root, { open: true, onDismiss });
		// The item's own handler re-renders it away before the click reaches
		// the document, as a {#if} branch swap does.
		item.addEventListener('click', () => item.remove());
		item.click();
		expect(onDismiss).not.toHaveBeenCalled();
	});

	it('does nothing while closed', () => {
		const { root, outside } = setup();
		const onDismiss = vi.fn();
		dismissable(root, { open: false, onDismiss });
		outside.click();
		escape();
		expect(onDismiss).not.toHaveBeenCalled();
	});

	it('follows open through update()', () => {
		const { root, outside } = setup();
		const onDismiss = vi.fn();
		const action = dismissable(root, { open: false, onDismiss });
		action.update({ open: true, onDismiss });
		outside.click();
		expect(onDismiss).toHaveBeenCalledOnce();
	});

	it('returns focus to the trigger when Escape closes a focused menu', () => {
		const { root, trigger, item } = setup();
		const onDismiss = vi.fn();
		dismissable(root, { open: true, onDismiss });
		item.focus();
		escape();
		expect(onDismiss).toHaveBeenCalledOnce();
		expect(document.activeElement).toBe(trigger);
	});

	it('leaves focus alone when it was elsewhere', () => {
		const { root, outside } = setup();
		dismissable(root, { open: true, onDismiss: vi.fn() });
		outside.focus();
		escape();
		expect(document.activeElement).toBe(outside);
	});

	it('removes its listeners on destroy', () => {
		const { root, outside } = setup();
		const onDismiss = vi.fn();
		dismissable(root, { open: true, onDismiss }).destroy();
		outside.click();
		expect(onDismiss).not.toHaveBeenCalled();
	});
});
