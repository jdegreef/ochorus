<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';

	/**
	 * The three ways into the library — every book, the series, the A–Z of
	 * authors and books — as one row of tabs on each of those pages, so a
	 * reader on /series can see it is one view of Books (the top nav lights
	 * Books there) and step across. Tabs, not a breadcrumb: a top-level shelf
	 * shows no visible trail (page-design A6); its BreadcrumbList stays in the
	 * page's JSON-LD. Labels are the nav words, already in every catalogue.
	 */
	type Tab = 'books' | 'series' | 'az';
	let { current }: { current: Tab } = $props();
	const t = i18n.t;

	const tabs: { id: Tab; href: string; label: () => string }[] = [
		{ id: 'books', href: '/books', label: () => t('nav.books') },
		{ id: 'series', href: '/series/', label: () => t('nav.series') },
		{ id: 'az', href: '/authors', label: () => t('nav.azIndex') }
	];
</script>

<nav class="library-tabs mb-6" aria-label={t('nav.books')}>
	<ul class="tab-strip flex gap-1">
		{#each tabs as tab (tab.id)}
			<li>
				<a
					href={localizeHref(tab.href)}
					class="tab-link"
					class:is-active={tab.id === current}
					aria-current={tab.id === current ? 'page' : undefined}>{tab.label()}</a
				>
			</li>
		{/each}
	</ul>
</nav>

<style>
	/* The book and author pages' sub-nav tab, on the same shared bottom rule. */
	.library-tabs {
		border-bottom: 1px solid var(--border);
	}
	.library-tabs ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.tab-link {
		display: inline-block;
		padding: 0.5rem 0.75rem;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px; /* the underline meets the row's own border */
		font-size: var(--fs-small);
		font-weight: 500;
		white-space: nowrap;
		color: var(--muted);
		text-decoration: none;
	}
	.tab-link:hover {
		color: var(--text);
	}
	.tab-link.is-active {
		color: var(--accent);
		border-bottom-color: var(--accent);
	}
</style>
