<script lang="ts">
	import { page } from '$app/stores';

	let { children } = $props();

	// Top-level admin sections — each has an index route. Books and languages are
	// drill-downs reached from the dashboard, so they aren't top-level items; the
	// nav highlights nothing while you're deep in one of those detail pages.
	const sections = [
		{ href: '/admin', label: 'Dashboard', exact: true },
		{ href: '/admin/import', label: 'Import document' },
		{ href: '/admin/coverage', label: 'Coverage matrix' },
		{ href: '/admin/review', label: 'Review queue' },
		{ href: '/admin/audit', label: 'Content audit' },
		{ href: '/admin/activity', label: 'Activity' },
		{ href: '/admin/engagement', label: 'Engagement' },
		{ href: '/admin/search', label: 'Search' },
		{ href: '/admin/users', label: 'Users' }
	];

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
				<span class="block text-h3 leading-tight text-text">Admin</span>
			</a>
		</div>

		<nav
			aria-label="Admin sections"
			class="flex gap-1 overflow-x-auto px-3 py-3 md:mt-2 md:flex-col md:overflow-visible"
		>
			{#each sections as s (s.href)}
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
