<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref, locales } from '$lib/paraglide/runtime';
	import BooksShelf from '$lib/components/BooksShelf.svelte';

	const t = i18n.t;

	let { data } = $props();

	// Self-referential canonical + hreflang: each localized copy of this
	// prerendered page points at ITSELF, not the English URL (which would
	// deindex the translations). Mirrors authors/[slug].
	const canonical = `${SITE_URL}${localizeHref('/books')}`;
	const alternates = locales.map((loc) => ({
		loc,
		href: `${SITE_URL}${localizeHref('/books', { locale: loc })}`
	}));
</script>

<svelte:head>
	<title>{t('nav.books')} — Ochorus</title>
	<meta name="description" content={t('books.metaDescription')} />
	<link rel="canonical" href={canonical} />
	{#each alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}/books" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('nav.books')} — Ochorus" />
	<meta property="og:description" content={t('books.metaDescription')} />
	<meta property="og:url" content={canonical} />
</svelte:head>

<BooksShelf books={data.books} loadError={data.loadError} />
