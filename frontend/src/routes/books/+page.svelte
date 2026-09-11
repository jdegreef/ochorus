<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { itemList, hreflangAll } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import BooksShelf from '$lib/components/BooksShelf.svelte';
	import Seo from '$lib/components/Seo.svelte';

	const t = i18n.t;

	let { data } = $props();
	const books = $derived<BookSummary[]>(data.books ?? []);

	// schema.org ItemList of the shelf — an ordered roster of the library so a
	// crawler sees the works, not an opaque grid. Built from the full set.
	const booksLd = $derived(
		itemList(
			t('nav.books'),
			books.map((b) => ({ name: b.title, url: localizeHref(`/books/${b.slug}`) }))
		)
	);

	// Self-referential canonical + hreflang: each localized copy of this
	// prerendered page points at ITSELF, not the English URL (which would
	// deindex the translations). Mirrors authors/[slug].
	const canonical = `${SITE_URL}${localizeHref('/books')}`;
	// Gated on ADVERTISED_LOCALES, not Paraglide's full `locales`: a locale that
	// is wired in the UI but has an empty catalog must not be advertised to
	// crawlers (see advertised-locales.ts). This page was claiming alternates
	// for draft locales while sitemap.xml, the detail pages and the footer all
	// correctly omitted them — two contradictory claims, with the wrong one on
	// the site's most-crawled pages.
	const hreflang = hreflangAll('/books');
</script>

<Seo
	title={`${t('books.metaTitle')} — Ochorus`}
	description={t('books.metaDescription')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/books.png`}
	structuredData={books.length ? [booksLd] : []}
/>

<BooksShelf books={data.books} loadError={data.loadError} />
