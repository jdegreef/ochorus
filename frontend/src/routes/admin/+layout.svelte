<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';

	let { children } = $props();

	// Top-level admin sections — each has an index route. Books and languages are
	// drill-downs reached from the dashboard, so they aren't top-level items; the
	// nav highlights nothing while you're deep in one of those detail pages.
	// `capability` is the grant that opens the section (mirrors the backend gate);
	// the rail shows only what the signed-in user can reach. UX only — the API
	// still authorises every request.
	const sections = [
		{ href: '/admin', label: 'Dashboard', exact: true, capability: 'reporting' },
		// Undelegated, super-admin-only levers (a founder decision, 2026-09-21):
		// document import and the reader-email broadcast section. Language admins do
		// content QA in their languages, not raw ingestion or outbound email — the
		// backend gates these on IsAdminEmail too, so hiding the nav only tidies UX.
		{ href: '/admin/import', label: 'Import document', superOnly: true },
		{ href: '/admin/coverage', label: 'Coverage matrix', capability: 'reporting' },
		{ href: '/admin/language-health', label: 'Language health', capability: 'reporting' },
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

	// Only the sections the signed-in user can reach: Help needs any admin access,
	// a super-only section needs the super-admin flag, the rest need the
	// capability their grant opens.
	const visible = $derived(
		sections.filter((s) =>
			s.anyAccess ? auth.hasAdminAccess : s.superOnly ? auth.isAdmin : auth.can(s.capability!)
		)
	);

	// Exact match for the dashboard root; prefix match for sections (so a future
	// /admin/coverage/… detail page keeps its parent highlighted).
	const isActive = (href: string, exact = false) => {
		const p = $page.url.pathname;
		return exact ? p === href : p === href || p.startsWith(href + '/');
	};
</script>

<svelte:head><meta name="robots" content="noindex" /></svelte:head>

<div class="md:flex md:items-start">
	<!-- Persistent admin navigation: a left rail on desktop, a scrollable pill row
	     on mobile. Sits inside the site chrome (same as the admin pages already do). -->
	<!-- Pinned below the app nav, not at viewport 0: the nav became sticky at
	     z-40, so `top-0` slid the rail's "Admin" header and first link behind it
	     — and `max-h-screen` with its own scroll meant no amount of scrolling
	     brought them back. -->
	<aside
		class="border-b border-border bg-surface md:sticky md:top-[var(--appnav-h,0px)] md:max-h-[calc(100vh_-_var(--appnav-h,0px))] md:w-56 md:shrink-0 md:self-start md:overflow-y-auto md:border-b-0 md:border-r"
	>
		<div class="px-5 pt-5">
			<a href="/admin" class="inline-block hover:no-underline">
				<span class="eyebrow block text-accent">Ochorus</span>
				<!-- A language admin (any non-super admin) sees "Language Admin"; the
				     super admin keeps "Admin". -->
				<span class="block text-h3 leading-tight text-text">{auth.adminLabel}</span>
			</a>
		</div>

		<nav
			aria-label="Admin sections"
			class="flex gap-1 overflow-x-auto px-3 py-3 md:mt-2 md:flex-col md:overflow-visible"
		>
			{#each visible as s (s.href)}
				{@const active = isActive(s.href, s.exact)}
				<a
					href={s.href}
					aria-current={active ? 'page' : undefined}
					class="shrink-0 whitespace-nowrap rounded-sm px-3 py-2 text-small font-semibold transition-colors hover:no-underline {active
						? 'bg-accent-soft text-accent'
						: 'text-muted hover:bg-surface-2 hover:text-text'}"
				>
					{s.label}
				</a>
			{/each}
		</nav>

		<div class="hidden px-3 pb-4 md:block">
			<a
				href="/"
				class="inline-block rounded-sm px-3 py-2 text-small text-muted transition-colors hover:text-accent"
				>← View site</a
			>
		</div>
	</aside>

	<div class="min-w-0 flex-1">
		{@render children()}
	</div>
</div>
