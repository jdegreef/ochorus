import { describe, expect, it } from 'vitest';
import { adminWorkHref } from './adminLinks';
import { adminBookHref } from './library-admin';

describe('adminWorkHref', () => {
	it('builds the same book URL the admin itself uses', () => {
		expect(adminWorkHref('book', 'the-pursuit-of-god')).toBe(adminBookHref('the-pursuit-of-god'));
	});
	it('points a sermon at the admin sermon page', () => {
		expect(adminWorkHref('sermon', 'do-you-pray')).toBe('/admin/sermons/do-you-pray');
	});
});
