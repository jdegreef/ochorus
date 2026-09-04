<script lang="ts">
	import type { Hreflang } from '$lib/seo';

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
		/** Absolute raster image URL for social cards; omit when the page has none. */
		ogImage?: string;
		/** og:image pixel dimensions — pass both when the image size is known so
		 *  scrapers can lay the card out without fetching the file first. Only the
		 *  house 1200×630 OG rasters carry these; omit for anything else. */
		ogImageWidth?: number;
		ogImageHeight?: number;
		/** Ready-to-inject <script type="application/ld+json"> strings — build them
		 *  with jsonLd() so `<` is escaped before it reaches {@html}. */
		structuredData?: string[];
	} = $props();
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={canonical} />
	{#each hreflang.alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href={hreflang.xDefault} />
	<meta property="og:type" content={ogType} />
	<meta property="og:title" content={ogTitle} />
	<meta property="og:description" content={description} />
	<meta property="og:url" content={canonical} />
	{#if ogImage}
		<meta property="og:image" content={ogImage} />
		{#if ogImageWidth && ogImageHeight}
			<meta property="og:image:width" content={String(ogImageWidth)} />
			<meta property="og:image:height" content={String(ogImageHeight)} />
		{/if}
		<!-- Explicit twitter:image rather than leaning on the og:image fallback:
		     stated, it's the value some scrapers key on. -->
		<meta name="twitter:image" content={ogImage} />
	{/if}
	<meta name="twitter:card" content={ogImage ? 'summary_large_image' : 'summary'} />
	{#each structuredData as ld, i (i)}
		<!-- Server-built, entity-escaped JSON-LD (see seo.ts jsonLd()); never user input. -->
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		{@html ld}
	{/each}
</svelte:head>
