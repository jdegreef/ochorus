<script lang="ts">
	import type { Hreflang } from '$lib/seo';
	import { SITE_URL } from '$lib/config';

	// Site-wide social-card fallback. Pages with their own art (a book cover, a
	// portrait, a sermon's og twin) pass `ogImage`; everything else — the home
	// page, chapter pages, the utility/list pages without a bespoke card — shared
	// a bare text card before this, so a link to the site's most-linked pages
	// previewed as nothing. The 1200×630 default lives in /static/og.
	const DEFAULT_OG = `${SITE_URL}/og/default.png`;

	// Central <head> for a prerendered public page: title, description, canonical,
	// hreflang alternates + x-default, Open Graph / Twitter cards, and any JSON-LD
	// blocks. SvelteKit hoists a child component's <svelte:head> into the document
	// head at prerender time, so every detail route emits identical, correct head
	// markup from one place instead of six hand-kept copies that drifted (the
	// hreflang bug lived in four of them).
	let {
		title,
		description,
		canonical,
		hreflang,
		ogType = 'website',
		ogTitle = title,
		ogImage = '',
		ogImageAlt = '',
		ogImageWidth,
		ogImageHeight,
		structuredData = []
	}: {
		/** The full <title> text (routes append " — Ochorus" themselves). */
		title: string;
		description: string;
		canonical: string;
		hreflang: Hreflang;
		/** Open Graph object type (book / article / website / profile). */
		ogType?: string;
		/** og:title — defaults to the page title when a route doesn't override it. */
		ogTitle?: string;
		/** Absolute raster image URL for social cards; omit to use the site default. */
		ogImage?: string;
		/** Alt text for the social card image (og:image:alt / twitter:image:alt) —
		 *  what the card depicts (a cover, a portrait) for scrapers and screen
		 *  readers that surface it. Omit to leave the image unlabelled. */
		ogImageAlt?: string;
		/** og:image pixel dimensions — pass both when the image size is known so
		 *  scrapers can lay the card out without fetching the file first. Only the
		 *  house 1200×630 OG rasters carry these; omit for anything else. */
		ogImageWidth?: number;
		ogImageHeight?: number;
		/** Ready-to-inject <script type="application/ld+json"> strings — build them
		 *  with jsonLd() so `<` is escaped before it reaches {@html}. */
		structuredData?: string[];
	} = $props();

	// Resolve the card image once. The default is a 1200×630 house raster, so it
	// carries the same dimension hints the bespoke OG rasters do; a caller's own
	// image only advertises dimensions when it passed them.
	const card = $derived(ogImage || DEFAULT_OG);
	const cardWidth = $derived(ogImage ? ogImageWidth : 1200);
	const cardHeight = $derived(ogImage ? ogImageHeight : 630);
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={canonical} />
	{#each hreflang.alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href={hreflang.xDefault} />
	<!-- og:site_name names the publication behind the card, so a share renders
	     "Ochorus" under the title instead of a bare hostname; stated once here for
	     every prerendered page. -->
	<meta property="og:site_name" content="Ochorus" />
	<meta property="og:type" content={ogType} />
	<meta property="og:title" content={ogTitle} />
	<meta property="og:description" content={description} />
	<meta property="og:url" content={canonical} />
	<meta property="og:image" content={card} />
	{#if ogImageAlt}
		<meta property="og:image:alt" content={ogImageAlt} />
	{/if}
	{#if cardWidth && cardHeight}
		<meta property="og:image:width" content={String(cardWidth)} />
		<meta property="og:image:height" content={String(cardHeight)} />
	{/if}
	<!-- Twitter card fields. The card only inherited the image before, so a shared
	     link showed the picture under a scraper-guessed title and blurb; title and
	     description mirror the Open Graph values so the card reads deliberately.
	     Explicit twitter:image rather than leaning on the og:image fallback:
	     stated, it's the value some scrapers key on. -->
	<meta name="twitter:title" content={ogTitle} />
	<meta name="twitter:description" content={description} />
	<meta name="twitter:image" content={card} />
	{#if ogImageAlt}
		<meta name="twitter:image:alt" content={ogImageAlt} />
	{/if}
	<meta name="twitter:card" content="summary_large_image" />
	{#each structuredData as ld, i (i)}
		<!-- Server-built, entity-escaped JSON-LD (see seo.ts jsonLd()); never user input. -->
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		{@html ld}
	{/each}
</svelte:head>
