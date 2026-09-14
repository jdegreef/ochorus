import { describe, it, expect } from 'vitest';
import { can, hasAnyAdminAccess, type AdminScope } from './adminAccess';

const reviewerEs: AdminScope[] = [
	{ capability: 'review', verb: 'act', languages: ['es'], role: 'reviewer' },
	{ capability: 'reporting', verb: 'view', languages: ['*'], role: 'reviewer' }
];

describe('can', () => {
	it('a super admin ("all") can do anything', () => {
		expect(can('all', 'language_admin', 'approve', 'pt')).toBe(true);
		expect(can('all', 'anything', 'act')).toBe(true);
	});

	it('honours the verb ladder', () => {
		expect(can(reviewerEs, 'review', 'view', 'es')).toBe(true);
		expect(can(reviewerEs, 'review', 'act', 'es')).toBe(true);
		expect(can(reviewerEs, 'review', 'approve', 'es')).toBe(false); // act < approve
	});

	it('honours language scope', () => {
		expect(can(reviewerEs, 'review', 'act', 'es')).toBe(true);
		expect(can(reviewerEs, 'review', 'act', 'pt')).toBe(false); // not granted pt
		expect(can(reviewerEs, 'reporting', 'view', 'pt')).toBe(true); // '*' covers all
	});

	it('a non-language-scoped check passes on capability+verb alone', () => {
		expect(can(reviewerEs, 'review', 'act')).toBe(true);
	});

	it('denies capabilities not granted', () => {
		expect(can(reviewerEs, 'users', 'view')).toBe(false);
		expect(can(reviewerEs, 'publish', 'act', 'es')).toBe(false);
	});

	it('defaults the required verb to view', () => {
		expect(can(reviewerEs, 'reporting')).toBe(true);
		expect(can([], 'reporting')).toBe(false);
	});
});

describe('hasAnyAdminAccess', () => {
	it('is true for a super admin and any grant, false for none', () => {
		expect(hasAnyAdminAccess('all')).toBe(true);
		expect(hasAnyAdminAccess(reviewerEs)).toBe(true);
		expect(hasAnyAdminAccess([])).toBe(false);
	});
});
