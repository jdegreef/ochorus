/**
 * Pure helpers behind the /admin/team console — kept out of the page so the
 * parts that decide what a grant or an undo does are unit-tested.
 */
import type { TeamMember } from '$lib/library-admin';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

// Misspellings of the providers our team actually signs in with. A grant is
// keyed by email and activates on sign-in, so a typo grants access to nobody
// and nothing ever says so — catch the common ones before they're saved.
const DOMAIN_TYPOS: Record<string, string> = {
	'gmial.com': 'gmail.com',
	'gmai.com': 'gmail.com',
	'gamil.com': 'gmail.com',
	'gnail.com': 'gmail.com',
	'gmail.co': 'gmail.com',
	'gmail.con': 'gmail.com',
	'hotmial.com': 'hotmail.com',
	'yahooo.com': 'yahoo.com',
	'outlok.com': 'outlook.com'
};

/** Why `addr` can't be granted yet, or '' when it looks fine. */
export function emailProblem(addr: string): string {
	const a = addr.trim().toLowerCase();
	if (!a) return '';
	if (!EMAIL.test(a)) return 'That doesn’t look like an email address.';
	const domain = a.split('@')[1];
	const fix = DOMAIN_TYPOS[domain];
	return fix ? `"${domain}" looks like a typo. Did you mean ${fix}?` : '';
}

/** Every language a member's grants reach, sorted ("*" for all) — only the
 *  role rows when `rolesOnly`, which are what a new role grant replaces. */
export function memberLanguages(m: TeamMember, rolesOnly = false): string[] {
	const scopes = rolesOnly ? m.scopes.filter((s) => s.role) : m.scopes;
	return [...new Set(scopes.flatMap((s) => s.languages))].sort();
}

/** The languages every one of a member's grants shares, or null when they
 *  differ — so a row can name the scope once instead of on every permission. */
export function sharedLanguages(m: TeamMember): string[] | null {
	const keys = new Set(m.scopes.map((s) => [...s.languages].sort().join(',')));
	return keys.size === 1 ? [...m.scopes[0].languages].sort() : null;
}
