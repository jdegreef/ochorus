import { describe, expect, it, vi } from 'vitest';
import { createBackStack } from './back';
import { onBack } from './index';

describe('the Back stack', () => {
	it('closes the most recently opened overlay first', () => {
		const s = createBackStack();
		const drawer = vi.fn();
		const menu = vi.fn();
		s.push(drawer);
		s.push(menu);
		expect(s.pop()).toBe(true);
		expect(menu).toHaveBeenCalledTimes(1);
		expect(drawer).not.toHaveBeenCalled();
		expect(s.pop()).toBe(true);
		expect(drawer).toHaveBeenCalledTimes(1);
		expect(s.pop()).toBe(false);
	});

	it('forgets an overlay that closed some other way', () => {
		const s = createBackStack();
		const drawer = vi.fn();
		const popover = vi.fn();
		s.push(drawer);
		const off = s.push(popover);
		off();
		off(); // twice is harmless
		s.pop();
		expect(popover).not.toHaveBeenCalled();
		expect(drawer).toHaveBeenCalledTimes(1);
	});

	it('drops an overlay that does not close, so Back is never stuck', () => {
		const s = createBackStack();
		s.push(() => {});
		expect(s.pop()).toBe(true);
		expect(s.size).toBe(0);
		expect(s.pop()).toBe(false);
	});

	it('registers nothing on the website', () => {
		const close = vi.fn();
		const off = onBack(close);
		expect(typeof off).toBe('function');
		off();
		expect(close).not.toHaveBeenCalled();
	});
});
