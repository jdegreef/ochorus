<script lang="ts">
	import type { ArticleSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, hreflangFor } from '$lib/seo';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import ArticleShelf from '$lib/components/ArticleShelf.svelte';
	import { articleHasTopic, articleCollectionLd } from '$lib/articleTopics';
	import { i18n } from '$lib/i18n.svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	// English literals, as on /quotes and /scripture: this index is not localized
	// because what it lists is not (articles are English-only for now).
	let { data } = $props();
	const articles = $derived<ArticleSummary[]>(data.articles);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	// The topic filter is now a real path — the chips in <ArticleShelf> link to
	// `/articles/<slug>/`. Old shared links carrying the retired `?topic=<slug>`
	// query are forwarded to the clean URL so they don't silently show "All".
	// An $effect only runs in the browser, so this never touches the query string
	// during prerender (which SvelteKit forbids, and which the bare /articles must
	// not depend on anyway).
	$effect(() => {
		const wanted = $page.url.searchParams.get('topic');
		if (!wanted) return;
		const known = articles.some((a) => articleHasTopic(a, wanted));
		goto(known ? `/articles/${wanted}/` : '/articles/', { replaceState: true });
	});

	const path = '/articles/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);

	const title = 'Articles on prayer, faith & the Christian life — Ochorus';
	const description =
		'Short, plain-spoken readings on prayer, faith, grace and the life with God — ' +
		'each one pointing you to a classic Christian book, sermon or life worth reading in full, ' +
		'free.';

	const crumbs = [
		{ name: 'Home', href: '/' },
		{ name: 'Articles', href: path }
	];
	const crumbsLd = breadcrumbLd(crumbs);
	// A CollectionPage listing each article, so the set reads as one entity to a
	// crawler rather than a handful of unrelated URLs.
	const listLd = $derived(articleCollectionLd('Articles', description, canonical, articles));
</script>

<Seo {title} {description} {canonical} {hreflang} structuredData={[crumbsLd, listLd]} />

<div class="page-col px-5 py-10">
	<!-- No visible breadcrumb: a top-level hub's only trail is Home > <this>
	     — Home is already the logo, <this> restates the H1 below, so it
	     carries nothing. The BreadcrumbList JSON-LD stays in the head; the
	     page's position is true even when we don't draw it. -->
	<PageHeader
		title="Articles"
		tagline="Short readings on prayer, faith and the life with God — each one written to send you on to a classic worth reading in full."
	/>

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if articles.length}
		<ArticleShelf {articles} activeTopic="" />
	{:else}
		<EmptyState message="No articles yet — check back soon." />
	{/if}
</div>
