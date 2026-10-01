import { describe, expect, it } from 'vitest';
import type { AdminScope } from './adminAccess';
import { ABILITIES, hasAbility, humanize, languageNames } from './adminHelp';
import { ADMIN_SECTIONS, opensSection } from './adminSections';

const reviewer: AdminScope[] = [
	{
		capability: 'reporting',
		verb: 'view',
		languages: ['es'],
		role: 'reviewer'
	},
	{ capability: 'review', verb: 'act', languages: ['es'], role: 'reviewer' },
	{
		capability: 'translate',
		verb: 'suggest',
		languages: ['es'],
		role: 'reviewer'
	}
];
const ability = (label: string) => ABILITIES.find((a) => a.label.startsWith(label))!;

describe('hasAbility', () => {
	it('follows the verb ladder', () => {
		expect(hasAbility(ability('Record review'), reviewer, false)).toBe(true);
		expect(hasAbility(ability('Confirm other'), reviewer, false)).toBe(false);
		expect(hasAbility(ability('File translation'), reviewer, false)).toBe(true);
	});

	it('keeps super-only abilities to the super admin, whatever the grants', () => {
		const grant = ability('Grant access');
		expect(hasAbility(grant, reviewer, false)).toBe(false);
		expect(hasAbility(grant, 'all', true)).toBe(true);
	});
});

describe('opensSection', () => {
	const viewer = (scopes: AdminScope[]) => ({
		isAdmin: false,
		hasAdminAccess: scopes.length > 0,
		can: (c: string) => scopes.some((s) => s.capability === c)
	});
	const open = (scopes: AdminScope[]) =>
		ADMIN_SECTIONS.filter((s) => opensSection(s, viewer(scopes))).map((s) => s.href);

	it('opens what the grants open and never a super-only section', () => {
		const sections = open(reviewer);
		expect(sections).toContain('/admin/review');
		expect(sections).toContain('/admin/help');
		expect(sections).not.toContain('/admin/users');
		expect(sections).not.toContain('/admin/team');
	});
});

describe('labels', () => {
	it('humanizes a code and names languages', () => {
		expect(humanize('content_edit')).toBe('Content edit');
		expect(languageNames(['es', 'xx'], { es: 'Spanish' })).toEqual(['Spanish', 'xx']);
		expect(languageNames(['*'], {})).toEqual(['All languages']);
	});
});
