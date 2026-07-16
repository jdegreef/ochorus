<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { i18n } from '$lib/i18n.svelte';
	import BooksShelf from '$lib/components/BooksShelf.svelte';

	const t = i18n.t;

	let { data } = $props();
</script>

<svelte:head>
	<title>{t('nav.books')} — Ochorus</title>
	<meta
		name="description"
		content="Browse the Ochorus library — classic Christian books by Andrew Murray, Charles Spurgeon, Watchman Nee, Hannah Whitall Smith and more. Free to read."
	/>
	<link rel="canonical" href="{SITE_URL}/books" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('nav.books')} — Ochorus" />
	<meta property="og:url" content="{SITE_URL}/books" />
</svelte:head>

<BooksShelf books={data.books} loadError={data.loadError} />
