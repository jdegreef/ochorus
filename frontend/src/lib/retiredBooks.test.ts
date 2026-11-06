import { describe, expect, it } from 'vitest';
import { retiredBookPath } from './retiredBooks';

describe('retiredBookPath', () => {
	it('sends a retired book page to its successor', () => {
		expect(retiredBookPath('lord-teach-us-to-pray-2')).toBe('/books/school-of-prayer/');
	});

	it('sends a retired chapter to the same lesson in the successor', () => {
		expect(retiredBookPath('lord-teach-us-to-pray-2', 1)).toBe('/books/school-of-prayer/2');
		expect(retiredBookPath('lord-teach-us-to-pray-2', 4, true)).toBe('/books/school-of-prayer/modern/5');
	});

	it('falls back to the book page for a non-numeric chapter', () => {
		expect(retiredBookPath('lord-teach-us-to-pray-2', Number('x'))).toBe('/books/school-of-prayer/');
	});

	it('leaves every other slug alone', () => {
		expect(retiredBookPath('school-of-prayer')).toBeNull();
		expect(retiredBookPath('toString')).toBeNull();
	});
});
