import { describe, it, expect } from 'vitest';
import { emailProblem, memberLanguages, sharedLanguages } from './adminTeam';
import type { TeamMember } from './library-admin';

const member = (scopes: TeamMember['scopes']): TeamMember => ({
	email: 'h@example.org',
	scopes,
	roles: [...new Set(scopes.map((s) => s.role).filter(Boolean))],
	outdated: []
});

describe('emailProblem', () => {
	it('accepts a plain address and stays quiet while empty', () => {
		expect(emailProblem('hannah@example.org')).toBe('');
		expect(emailProblem('  ')).toBe('');
	});

	it('rejects something that is not an address', () => {
		expect(emailProblem('hannah')).not.toBe('');
		expect(emailProblem('hannah@example')).not.toBe('');
	});

	it('suggests the provider a typo meant', () => {
		expect(emailProblem('Hannah@GMIAL.com')).toContain('gmail.com');
	});
});

describe('memberLanguages', () => {
	it('unions every scope, once each, sorted', () => {
		const m = member([
			{
				capability: 'review',
				verb: 'act',
				languages: ['lg', 'en'],
				role: 'reviewer'
			},
			{ capability: 'reporting', verb: 'view', languages: ['en'], role: '' }
		]);
		expect(memberLanguages(m)).toEqual(['en', 'lg']);
		expect(memberLanguages(m, true)).toEqual(['en', 'lg']);
		expect(memberLanguages({ ...m, scopes: m.scopes.slice(1) }, true)).toEqual([]);
	});
});

describe('sharedLanguages', () => {
	it('names the scope once when every grant agrees, else null', () => {
		const a = { capability: 'audit', verb: 'act', languages: ['lg', 'en'], role: 'reviewer' };
		const b = { capability: 'review', verb: 'act', languages: ['en', 'lg'], role: 'reviewer' };
		expect(sharedLanguages(member([a, b]))).toEqual(['en', 'lg']);
		expect(sharedLanguages(member([a, { ...b, languages: ['*'] }]))).toBeNull();
		expect(sharedLanguages(member([]))).toBeNull();
	});
});
