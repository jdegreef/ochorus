import { describe, expect, it } from 'vitest';

import { can, type Scopes } from './adminAccess';
import { ADMIN_SECTIONS, opensSection, sectionRequirement } from './adminSections';

const scope = (capability: string, verb: string) => ({
	capability,
	verb,
	languages: ['*'],
	role: ''
});
const viewer = (scopes: Scopes, isAdmin = false) => ({
	isAdmin,
	hasAdminAccess: isAdmin || (scopes !== 'all' && scopes.length > 0),
	can: (c: string, v?: string) => can(scopes, c, v)
});
const section = (href: string) => ADMIN_SECTIONS.find((s) => s.href === href)!;

describe('opensSection with a verb', () => {
	const contentAdmin = viewer([scope('publish', 'approve'), scope('email', 'approve')]);
	const languageAdmin = viewer([scope('publish', 'act'), scope('reporting', 'view')]);

	it('opens import and email to a content admin', () => {
		expect(opensSection(section('/admin/import'), contentAdmin)).toBe(true);
		expect(opensSection(section('/admin/emails/compose'), contentAdmin)).toBe(true);
	});

	it('keeps import and email from a language admin one rung below', () => {
		expect(opensSection(section('/admin/import'), languageAdmin)).toBe(false);
		expect(opensSection(section('/admin/emails'), languageAdmin)).toBe(false);
	});

	it('keeps Team & access super-admin only', () => {
		expect(opensSection(section('/admin/team'), contentAdmin)).toBe(false);
		expect(opensSection(section('/admin/team'), viewer('all', true))).toBe(true);
	});

	it('names the verb a section needs', () => {
		expect(sectionRequirement(section('/admin/import'), (c) => c)).toBe('Needs publish · Approve');
		expect(sectionRequirement(section('/admin/emails'), (c) => c)).toBe('Needs email');
	});
});
