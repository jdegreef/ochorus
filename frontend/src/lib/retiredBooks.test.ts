import { describe, expect, it } from 'vitest';
import { retiredBookPath, retiredChapterHref } from './retiredBooks';

describe('retiredBookPath', () => {
	it('sends a retired book page to its successor', () => {
		expect(retiredBookPath('lord-teach-us-to-pray-2')).toBe('/books/school-of-prayer/');
	});

	it('sends a retired chapter to the same lesson in the successor', () => {
		expect(retiredBookPath('lord-teach-us-to-pray-2', 1)).toBe('/books/school-of-prayer/2');
		expect(retiredBookPath('lord-teach-us-to-pray-2', 4)).toBe('/books/school-of-prayer/5');
	});

	it('forwards only the chapters the retired book had', () => {
		for (const order of [0, 5, 12, -1, 1.5, Number('x')]) {
			expect(retiredBookPath('lord-teach-us-to-pray-2', order)).toBeNull();
		}
	});

	it('keeps plan context but drops the paragraph and edition on a chapter link', () => {
		expect(retiredChapterHref('lord-teach-us-to-pray-2', 2, '?plan=school-of-prayer&day=2&p=7')).toBe(
			'/books/school-of-prayer/3?plan=school-of-prayer&day=2'
		);
		expect(retiredChapterHref('lord-teach-us-to-pray-2', 2, '?p=7&edition=modern')).toBe('/books/school-of-prayer/3');
		expect(retiredChapterHref('lord-teach-us-to-pray-2', 2, '')).toBe('/books/school-of-prayer/3');
		expect(retiredChapterHref('lord-teach-us-to-pray-2', 9, '?plan=x')).toBeNull();
		expect(retiredChapterHref('school-of-prayer', 2, '?plan=x')).toBeNull();
	});

	it('leaves every other slug alone', () => {
		expect(retiredBookPath('school-of-prayer')).toBeNull();
		expect(retiredBookPath('school-of-prayer', 2)).toBeNull();
		expect(retiredBookPath('toString')).toBeNull();
	});
});
