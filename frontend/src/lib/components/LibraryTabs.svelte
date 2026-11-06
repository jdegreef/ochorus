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
	 *
	 * `browse` is the Books shelf's own pair (design review #11): there the
	 * Books tab splits into Browse (the curated rows /books opens on) and
	 * "All N books" (the full grid with its filters, `?shelf=all`), so the
	 * grid is one tab away and the tab a reader is on says which view it is.
	 */
	type Tab = 'books' | 'series' | 'az' | 'bios';
	let {
		current,
		series = true,
		set = 'library',
		browse
	}: {
		current: Tab;
		series?: boolean;
		set?: 'library' | 'writers';
		/** On /books: the library's size, and whether the full grid is showing. */
		browse?: { count: number; all: boolean };
	} = $props();
	const t = i18n.t;

	type Item = { id: string; href: string; label: string; active: boolean };
	const tabs = $derived<Item[]>(
		set === 'writers'
			? [
					{ id: 'bios', href: '/biographies', label: t('nav.biographies'), active: current === 'bios' },
					{ id: 'az', href: '/authors', label: t('nav.azIndex'), active: current === 'az' }
				]
			: [
					...(browse
						? [
								{ id: 'browse', href: '/books', label: t('books.browse'), active: !browse.all },
								{
									id: 'all',
									href: '/books?shelf=all',
									label: t('books.allCount').replace('%n%', String(browse.count)),
									active: browse.all
								}
							]
						: [{ id: 'books', href: '/books', label: t('nav.books'), active: current === 'books' }]),
					{ id: 'series', href: '/series/', label: t('nav.series'), active: current === 'series' },
					{ id: 'az', href: '/authors', label: t('nav.azIndex'), active: current === 'az' }
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
					class:is-active={tab.active}
					aria-current={tab.active ? 'page' : undefined}>{tab.label}</a
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
