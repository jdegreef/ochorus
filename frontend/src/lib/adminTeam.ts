/**
 * Pure helpers behind the /admin/team console — kept out of the page so the
 * parts that decide what a grant or an undo does are unit-tested.
 */
import type { TeamMember } from '$lib/library-admin';
import { relativeTime } from '$lib/relativeTime';

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

const DAY = 86_400_000;

// The admin is English-only; the same formatter the Users page shows "last seen" with.
const ago = (iso: string, now: number) => relativeTime(Date.parse(iso), 'en', 'just now', now);

export type SignInStatus = { label: string; tone: 'ok' | 'warn' | 'idle' };

/** Whether a member's grant is in use. A grant only works once that exact
 *  address signs in, so "never" is the case worth flagging; a long silence is
 *  shown plainly for the access review rather than as an error. */
export function signInStatus(
	m: { last_seen_at: string | null; granted_at: string | null },
	now = Date.now()
): SignInStatus {
	if (!m.last_seen_at) {
		const since = m.granted_at ? `Invited ${ago(m.granted_at, now)}` : 'Invited';
		return { label: `${since} · not signed in yet`, tone: 'warn' };
	}
	const days = (now - Date.parse(m.last_seen_at)) / DAY;
	return days <= 30
		? { label: `Active · seen ${ago(m.last_seen_at, now)}`, tone: 'ok' }
		: { label: `Last seen ${ago(m.last_seen_at, now)}`, tone: 'idle' };
}

/** A history event's languages as a codes list, whatever shape was logged. */
export const historyLanguages = (raw: string[] | string): string[] =>
	(Array.isArray(raw) ? raw : raw.split(',')).map((c) => c.trim()).filter(Boolean);
