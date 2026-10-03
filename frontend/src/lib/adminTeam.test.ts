import { describe, it, expect } from 'vitest';
import { emailProblem, historyLanguages, memberLanguages, sharedLanguages, signInStatus } from './adminTeam';
import type { TeamMember } from './library-admin';

const member = (scopes: TeamMember['scopes']): TeamMember => ({
	email: 'h@example.org',
	scopes,
	roles: [...new Set(scopes.map((s) => s.role).filter(Boolean))],
	outdated: [],
	last_seen_at: null,
	granted_at: null,
	granted_by: '',
	history: []
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

describe('signInStatus', () => {
	const now = Date.parse('2026-10-02T12:00:00Z');
	const daysAgo = (n: number) => new Date(now - n * 86_400_000).toISOString();

	it('flags a grant nobody has signed in to', () => {
		expect(signInStatus({ last_seen_at: null, granted_at: daysAgo(16) }, now)).toEqual({
			label: 'Invited 16 days ago · not signed in yet',
			tone: 'warn'
		});
	});

	it('is active within 30 days, then just says when', () => {
		expect(signInStatus({ last_seen_at: daysAgo(3), granted_at: null }, now)).toEqual({
			label: 'Active · seen 3 days ago',
			tone: 'ok'
		});
		expect(signInStatus({ last_seen_at: daysAgo(74), granted_at: null }, now).tone).toBe('idle');
		expect(signInStatus({ last_seen_at: daysAgo(1), granted_at: null }, now).label).toBe('Active · seen yesterday');
	});
});

describe('historyLanguages', () => {
	it('reads a list, a "*" or a comma string', () => {
		expect(historyLanguages(['en', 'lg'])).toEqual(['en', 'lg']);
		expect(historyLanguages('*')).toEqual(['*']);
		expect(historyLanguages('en, lg')).toEqual(['en', 'lg']);
	});
});
