/**
 * The admin rail's top-level sections — one list, read by the rail
 * (`routes/admin/+layout.svelte`) and by the Help page's "Where things live"
 * map, so the two can't disagree about what a grant opens.
 *
 * `capability` is the grant that opens the section (mirrors the backend gate);
 * `superOnly` marks an undelegated super-admin lever; `anyAccess` is shown to
 * anyone with any admin access. UX only — the API still authorises every
 * request.
 */
export interface AdminSection {
	href: string;
	label: string;
	exact?: boolean;
	capability?: string;
	superOnly?: boolean;
	anyAccess?: boolean;
}

// Books and languages are drill-downs reached from the dashboard, so they
// aren't top-level items.
export const ADMIN_SECTIONS: AdminSection[] = [
	{ href: '/admin', label: 'Dashboard', exact: true, capability: 'reporting' },
	// Undelegated, super-admin-only levers (a founder decision, 2026-09-21):
	// document import and the reader-email broadcast section. Language admins do
	// content QA in their languages, not raw ingestion or outbound email — the
	// backend gates these on IsAdminEmail too, so hiding the nav only tidies UX.
	{ href: '/admin/import', label: 'Import document', superOnly: true },
	{
		href: '/admin/coverage',
		label: 'Coverage matrix',
		capability: 'reporting'
	},
	{
		href: '/admin/language-health',
		label: 'Language health',
		capability: 'reporting'
	},
	{ href: '/admin/review', label: 'Review queue', capability: 'review' },
	{ href: '/admin/feedback', label: 'Feedback', capability: 'feedback' },
	{ href: '/admin/audit', label: 'Content audit', capability: 'audit' },
	{ href: '/admin/activity', label: 'Activity', capability: 'reporting' },
	{ href: '/admin/engagement', label: 'Engagement', capability: 'reporting' },
	{ href: '/admin/emails', label: 'Emails', superOnly: true, exact: true },
	{ href: '/admin/emails/compose', label: 'Compose email', superOnly: true },
	{ href: '/admin/search', label: 'Search', capability: 'reporting' },
	{ href: '/admin/users', label: 'Users', capability: 'users' },
	// Managing access is undelegated — super admins only (auth.isAdmin is the
	// super-admin flag; a scoped grantee is not is_admin).
	{ href: '/admin/team', label: 'Team & access', superOnly: true },
	// Help explains the admin system itself — shown to anyone with any admin
	// access, whatever their capabilities.
	{ href: '/admin/help', label: 'Help & roles', anyAccess: true }
];

/** The slice of the auth store the section check reads. */
export interface SectionViewer {
	isAdmin: boolean;
	hasAdminAccess: boolean;
	can(capability: string): boolean;
}

/**
 * Can this viewer open `section`? Help needs any admin access, a super-only
 * section needs the super-admin flag, the rest need the capability their grant
 * opens.
 */
export const opensSection = (section: AdminSection, viewer: SectionViewer): boolean =>
	section.anyAccess
		? viewer.hasAdminAccess
		: section.superOnly
			? viewer.isAdmin
			: viewer.can(section.capability!);

/** What opening `section` needs, in words — the same ladder as `opensSection`. */
export const sectionRequirement = (
	section: AdminSection,
	capabilityLabel: (code: string) => string
): string =>
	section.anyAccess
		? 'Needs any admin access'
		: section.superOnly
			? 'Super admin only'
			: `Needs ${capabilityLabel(section.capability!)}`;
