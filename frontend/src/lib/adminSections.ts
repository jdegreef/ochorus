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
	/** The rail heading it sits under (`ADMIN_GROUPS`). */
	group: AdminGroup;
	exact?: boolean;
	capability?: string;
	superOnly?: boolean;
	anyAccess?: boolean;
}

/** The rail's headings, in order. A flat list of two dozen links reads as a
 *  wall; grouped, the eye finds "where do I fix this" in one hop. */
export const ADMIN_GROUPS = ['Overview', 'Library', 'Quality', 'Audience', 'Outreach', 'Settings'] as const;
export type AdminGroup = (typeof ADMIN_GROUPS)[number];

// A single book, sermon or language is a drill-down (reached from these lists,
// the dashboard or the palette), so it isn't a top-level item itself.
export const ADMIN_SECTIONS: AdminSection[] = [
	{ href: '/admin', label: 'Dashboard', group: 'Overview', exact: true, capability: 'reporting' },
	{ href: '/admin/coverage', label: 'Coverage matrix', group: 'Overview', capability: 'reporting' },
	{ href: '/admin/language-health', label: 'Language health', group: 'Overview', capability: 'reporting' },
	{ href: '/admin/activity', label: 'Activity', group: 'Overview', capability: 'reporting' },

	// The inventory lists ($lib/adminCatalog): reporting views, like the book
	// and sermon admin pages they open.
	{ href: '/admin/books', label: 'Books', group: 'Library', capability: 'reporting' },
	{ href: '/admin/sermons', label: 'Sermons', group: 'Library', capability: 'reporting' },
	{ href: '/admin/authors', label: 'Authors', group: 'Library', capability: 'reporting' },
	{ href: '/admin/plans', label: 'Plans', group: 'Library', capability: 'reporting' },
	{ href: '/admin/topics', label: 'Topics', group: 'Library', capability: 'reporting' },
	{ href: '/admin/articles', label: 'Articles', group: 'Library', capability: 'reporting' },
	{ href: '/admin/quotes', label: 'Quotes', group: 'Library', capability: 'reporting' },
	{ href: '/admin/series', label: 'Series', group: 'Library', capability: 'reporting' },
	// Undelegated, super-admin-only levers (a founder decision, 2026-09-21):
	// document import and the reader-email broadcast section. Language admins do
	// content QA in their languages, not raw ingestion or outbound email — the
	// backend gates these on IsAdminEmail too, so hiding the nav only tidies UX.
	{ href: '/admin/import', label: 'Import document', group: 'Library', superOnly: true },

	{ href: '/admin/review', label: 'Review queue', group: 'Quality', capability: 'review' },
	{ href: '/admin/audit', label: 'Content audit', group: 'Quality', capability: 'audit' },
	{ href: '/admin/covers', label: 'Cover wall', group: 'Quality', capability: 'audit' },
	{ href: '/admin/feedback', label: 'Feedback', group: 'Quality', capability: 'feedback' },

	{ href: '/admin/engagement', label: 'Engagement', group: 'Audience', capability: 'reporting' },
	{ href: '/admin/search', label: 'Search', group: 'Audience', capability: 'reporting' },
	{ href: '/admin/users', label: 'Users', group: 'Audience', capability: 'users' },

	{ href: '/admin/emails', label: 'Emails', group: 'Outreach', superOnly: true, exact: true },
	{ href: '/admin/emails/compose', label: 'Compose email', group: 'Outreach', superOnly: true },
	{ href: '/admin/emails/automations', label: 'Automated emails', group: 'Outreach', superOnly: true },
	// The day's post for the WhatsApp channel: outbound, like the emails.
	{ href: '/admin/whatsapp', label: 'WhatsApp post', group: 'Outreach', superOnly: true },

	// Managing access is undelegated — super admins only (auth.isAdmin is the
	// super-admin flag; a scoped grantee is not is_admin).
	{ href: '/admin/team', label: 'Team & access', group: 'Settings', superOnly: true },
	// Help explains the admin system itself — shown to anyone with any admin
	// access, whatever their capabilities.
	{ href: '/admin/help', label: 'Help & roles', group: 'Settings', anyAccess: true }
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
	section.superOnly
		? 'Super admin only'
		: section.capability && !section.anyAccess
			? `Needs ${capabilityLabel(section.capability)}`
			: 'Needs any admin access';
