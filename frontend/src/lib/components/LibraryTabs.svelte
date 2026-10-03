<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { tabStrip } from '$lib/actions/tabStrip';
	import { localizeHref } from '$lib/href';

	/**
	 * The three ways into the library — every book, the series, the A–Z of
	 * authors and books — as one row of tabs on each of those pages, so a
	 * reader on /series can see it is one view of Books (the top nav lights
	 * Books there) and step across. Tabs, not a breadcrumb: a top-level shelf
	 * shows no visible trail (page-design A6); its BreadcrumbList stays in the
	 * page's JSON-LD. Labels are the nav words, already in every catalogue.
	 *
	 * `series` false drops the Series tab where the page knows this language has
	 * none (the Books shelf hides its own series links then), so the row never
	 * leads to an empty, unindexed shelf.
	 *
	 * `set="writers"` is the same row for the two indexes of the writers —
	 * Biographies (their lives) and the A–Z (their books) — on /biographies, so
	 * a reader there can see the alphabetical index exists and step across.
	 */
	type Tab = 'books' | 'series' | 'az' | 'bios';
	let {
		current,
		series = true,
		set = 'library'
	}: { current: Tab; series?: boolean; set?: 'library' | 'writers' } = $props();
	const t = i18n.t;

	const tabs = $derived(
		set === 'writers'
			? [
					{ id: 'bios' as const, href: '/biographies', label: t('nav.biographies') },
					{ id: 'az' as const, href: '/authors', label: t('nav.azIndex') }
				]
			: [
					{ id: 'books' as const, href: '/books', label: t('nav.books') },
					{ id: 'series' as const, href: '/series/', label: t('nav.series') },
					{ id: 'az' as const, href: '/authors', label: t('nav.azIndex') }
				].filter((tab) => series || tab.id !== 'series' || current === 'series')
	);

	// A long language can push the row past a phone's width; `tabStrip` fades
	// the edge that hides tabs and brings the current tab into view.
</script>

<!-- Named "Explore", not "Books": the primary nav already has a Books link,
     and /books' own heading says Books. -->
<nav class="library-tabs mb-6" aria-label={t('footer.explore')}>
	<ul class="tab-strip flex gap-1" use:tabStrip={undefined}>
		{#each tabs as tab (tab.id)}
			<li>
				<a
					href={localizeHref(tab.href)}
					class="subnav-link"
					class:is-active={tab.id === current}
					aria-current={tab.id === current ? 'page' : undefined}>{tab.label}</a
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
</style>
