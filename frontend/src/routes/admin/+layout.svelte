<script lang="ts">
	import { page } from '$app/stores';
	import { auth } from '$lib/auth.svelte';
	import { ADMIN_GROUPS, ADMIN_SECTIONS, opensSection } from '$lib/adminSections';
	import { SCRIPT_FONTS, linkSheet } from '$lib/fontSheets';
	import { onMount } from 'svelte';

	let { children } = $props();

	// Admin reviews every language's text on English pages, and each script's
	// faces load only on its own locale's pages ($lib/fontSheets) — so take all.
	onMount(() => Object.values(SCRIPT_FONTS).forEach(linkSheet));

	// Only the sections the signed-in user can reach (the list and the rule live
	// in $lib/adminSections, shared with the Help page's "Where things live").
	const visible = $derived(ADMIN_SECTIONS.filter((s) => opensSection(s, auth)));
	// Under their headings, in the groups' order; a group the viewer can open
	// nothing in is left out entirely rather than drawn as an empty heading.
	const groups = $derived(
		ADMIN_GROUPS.map((g) => ({ name: g, sections: visible.filter((s) => s.group === g) })).filter(
			(g) => g.sections.length
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

		<!-- Mobile: one scrollable pill row, as before. Desktop: the same links
		     under group headings — two dozen links in one column read as a wall. -->
		<nav
			aria-label="Admin sections"
			class="flex gap-1 overflow-x-auto px-3 py-3 md:mt-1 md:flex-col md:gap-0 md:overflow-visible"
		>
			{#each groups as g (g.name)}
				<p class="hidden px-3 pb-1 pt-3 text-micro font-semibold uppercase tracking-wide text-muted md:block">
					{g.name}
				</p>
				{#each g.sections as s (s.href)}
					{@const active = isActive(s.href, s.exact)}
					<a
						href={s.href}
						aria-current={active ? 'page' : undefined}
						class="shrink-0 whitespace-nowrap rounded-sm px-3 py-2 text-small font-semibold transition-colors hover:no-underline md:py-1.5 {active
							? 'bg-accent-soft text-accent'
							: 'text-muted hover:bg-surface-2 hover:text-text'}"
					>
						{s.label}
					</a>
				{/each}
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
