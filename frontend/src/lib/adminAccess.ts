/**
 * Frontend mirror of the backend's scoped-admin check (accounts.permissions).
 * Pure and unit-tested; the auth store holds the scopes and delegates here, and
 * the admin nav uses `can()` to show only the sections a user's grants open.
 *
 * This is UX, never the security boundary — the Django API is the real gate
 * (RequireCapability, per-endpoint). A stale or spoofed client scope only hides
 * or shows a menu item; every actual request is still authorised server-side.
 */

/** One grant as `/api/auth/me` returns it. */
export interface AdminScope {
	capability: string;
	verb: string;
	languages: string[];
	role: string;
}

/** A user's scopes: the literal `'all'` for a super admin, else their grants. */
export type Scopes = AdminScope[] | 'all';

/** The verb ladder, mirroring accounts.models.VERB_RANK. */
const VERB_RANK: Record<string, number> = { view: 0, suggest: 1, act: 2, approve: 3 };

/**
 * Can this set of scopes perform `verb` on `capability` (in `language`, when the
 * action is language-scoped)? `'all'` (super admin) always can. A grant satisfies
 * a requirement when its verb is at least as high on the ladder and its language
 * set covers the target (`'*'` = all).
 */
export function can(
	scopes: Scopes,
	capability: string,
	verb: string = 'view',
	language?: string
): boolean {
	if (scopes === 'all') return true;
	const need = VERB_RANK[verb] ?? 99;
	return scopes.some(
		(s) =>
			s.capability === capability &&
			(VERB_RANK[s.verb] ?? -1) >= need &&
			(language == null || s.languages.includes('*') || s.languages.includes(language))
	);
}

/** True if the scopes grant *any* admin access at all (drives "show the area"). */
export function hasAnyAdminAccess(scopes: Scopes): boolean {
	return scopes === 'all' || scopes.length > 0;
}
