/**
 * What the Help & roles page tells a viewer about their own access — pure, so
 * it's unit-tested apart from the page.
 *
 * The abilities are the handful of things people come to the admin to do, each
 * pinned to the (capability, verb) that permits it. `can()` from adminAccess
 * decides each one, the same check the rail and the API's gate make.
 */
import { can, type Scopes } from './adminAccess';

export interface Ability {
	label: string;
	capability: string;
	verb: string;
	/** Where you do it, when one page is the place. */
	href?: string;
	/** Undelegated: no grant opens it, only the super-admin allowlist. */
	superOnly?: boolean;
}

export const ABILITIES: Ability[] = [
	{
		label: 'See reports, coverage and the dashboard',
		capability: 'reporting',
		verb: 'view',
		href: '/admin'
	},
	{
		label: 'See the content audit',
		capability: 'audit',
		verb: 'view',
		href: '/admin/audit'
	},
	{
		label: 'File translation jobs',
		capability: 'translate',
		verb: 'suggest',
		href: '/admin/coverage'
	},
	{ label: 'File title-fix jobs', capability: 'content_edit', verb: 'suggest' },
	{
		label: 'Record review decisions',
		capability: 'review',
		verb: 'act',
		href: '/admin/review'
	},
	{
		label: 'Confirm other people’s reviews',
		capability: 'review',
		verb: 'approve',
		href: '/admin/review'
	},
	{
		label: 'Publish or unpublish editions',
		capability: 'publish',
		verb: 'act'
	},
	{
		label: 'Triage reader feedback',
		capability: 'feedback',
		verb: 'act',
		href: '/admin/feedback'
	},
	{
		label: 'See user analytics (names, emails)',
		capability: 'users',
		verb: 'view',
		href: '/admin/users'
	},
	{
		label: 'Grant access to others',
		capability: '',
		verb: '',
		href: '/admin/team',
		superOnly: true
	}
];

/** Does this viewer have `ability`? Super-only abilities need the allowlist flag. */
export const hasAbility = (ability: Ability, scopes: Scopes, isSuper: boolean): boolean =>
	ability.superOnly ? isSuper : can(scopes, ability.capability, ability.verb);

/** The verb ladder, lowest first — mirrors accounts.models.VERB_RANK. */
export const VERBS = ['view', 'suggest', 'act', 'approve'] as const;

/** "content_edit" → "Content edit"; the fallback when a label hasn't loaded. */
export const humanize = (code: string): string =>
	(code.charAt(0).toUpperCase() + code.slice(1)).replace(/_/g, ' ');

/** Role codes as people say them. */
export const ROLE_NAMES: Record<string, string> = {
	contributor: 'Contributor',
	reviewer: 'Reviewer',
	language_admin: 'Language admin',
	super_admin: 'Super admin'
};

/** One-line summaries shown beside each role. */
export const ROLE_SUMMARIES: Record<string, string> = {
	contributor:
		'Views the library and its queues; files translation and title-fix jobs. Applies nothing live.',
	reviewer: 'Everything a contributor can, plus records review decisions in their languages.',
	language_admin: 'Runs their languages: publishes, confirms reviews, triages feedback.',
	super_admin:
		'Everything, including granting access, user analytics, email and taking a language live.'
};

/** The grant's language list as names: `*` → "All languages". */
export const languageNames = (codes: string[], names: Record<string, string>): string[] =>
	codes.includes('*') ? ['All languages'] : codes.map((c) => names[c] ?? c);
