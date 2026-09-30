<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { OG_LOCALES, WEBSITE_ID, jsonLd, hreflangAll, publisherLd } from '$lib/seo';
	import { getLocale } from '$lib/paraglide/runtime';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { lang } from '$lib/lang.svelte';
	import { homeShareCardUrl } from '$lib/homeShareCard';
	import { auth } from '$lib/auth.svelte';
	import HomeMarketing from '$lib/components/HomeMarketing.svelte';
	import HomeDashboard from '$lib/components/HomeDashboard.svelte';

	let { data } = $props();

	const t = i18n.t;

	// Site-level structured data: a WebSite with the sitelinks-searchbox action
	// (the hero search posts to /search) and the publishing Organization.
	const siteLd = jsonLd([
		{
			'@context': 'https://schema.org',
			'@type': 'WebSite',
			'@id': WEBSITE_ID,
			name: 'Ochorus',
			url: `${SITE_URL}/`,
			// The same organisation every book, chapter and sermon names as
			// publisher — one entity, linked by @id ($lib/seo publisherLd).
			publisher: publisherLd(),
			potentialAction: {
				'@type': 'SearchAction',
				target: {
					'@type': 'EntryPoint',
					urlTemplate: `${SITE_URL}/search?q={search_term_string}`
				},
				'query-input': 'required name=search_term_string'
			}
		},
		{
			'@context': 'https://schema.org',
			...publisherLd(),
			description: t('home.metaDescription')
		}
	]);

	// Gated on ADVERTISED_LOCALES, not Paraglide's full `locales`: a locale that
	// is wired in the UI but has an empty catalog must not be advertised to
	// crawlers (see advertised-locales.ts). This page was claiming alternates
	// for draft locales while sitemap.xml, the detail pages and the footer all
	// correctly omitted them — two contradictory claims, with the wrong one on
	// the site's most-crawled pages.
	const hreflang = hreflangAll('/');
	// og:locale and its alternates, as Seo.svelte sets them on every other page.
	const ogLocale = OG_LOCALES[getLocale()];
	const ogAlternates = hreflang.alternates
		.map((a) => OG_LOCALES[a.loc])
		.filter((l) => l && l !== ogLocale);

	// One card per interface locale — homeShareCard.test holds every locale to
	// having its file.
	const shareCard = $derived(`${SITE_URL}${homeShareCardUrl(lang.current)}`);

	// Signed-in readers get a personal dashboard; everyone else — and every
	// crawler — gets the marketing home. The gate matters for SEO: this page is
	// prerendered, and during the build `auth.initialized` is false (auth only
	// resolves in the browser, on mount), so the baked HTML is always
	// <HomeMarketing>. The dashboard swaps in client-side once the session
	// resolves — the same "personal blocks appear at hydration" trade the home
	// page already made. `auth.initialized` also holds the marketing page in
	// place for the moment before a signed-in session is confirmed, rather than
	// flashing the dashboard to a reader who turns out to be logged out.
	const showDashboard = $derived(auth.enabled && auth.initialized && !!auth.user);

	// The head is identical for both views — the canonical home metadata is the
	// marketing page's, and the dashboard is a private, noindex-by-nature surface
	// rendered over the same URL.
</script>

<svelte:head>
	<title>Ochorus — {t('home.heroTitle')}</title>
	<meta name="description" content={t('home.metaDescription')} />
	<link rel="canonical" href="{SITE_URL}{localizeHref('/')}" />
	{#each hreflang.alternates as a (a.loc)}
		<link rel="alternate" hreflang={a.loc} href={a.href} />
	{/each}
	<link rel="alternate" hreflang="x-default" href={hreflang.xDefault} />
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content="Ochorus" />
	<meta property="og:title" content="Ochorus — {t('home.heroTitle')}" />
	<meta property="og:description" content={t('home.metaDescription')} />
	<meta property="og:url" content="{SITE_URL}{localizeHref('/')}" />
	{#if ogLocale}
		<meta property="og:locale" content={ogLocale} />
	{/if}
	{#each ogAlternates as l (l)}
		<meta property="og:locale:alternate" content={l} />
	{/each}
	<!-- Title and description stated for X too, as Seo.svelte does elsewhere:
	     left to the og fallback, some scrapers guess them from the page. -->
	<meta name="twitter:title" content="Ochorus — {t('home.heroTitle')}" />
	<meta name="twitter:description" content={t('home.metaDescription')} />
	<!-- The site's most-linked page shows the library itself: this language's
	     own covers on a shelf, under copy in this language — drawn per locale
	     by scripts/generate-home-og.mjs. This page hand-rolls its head rather
	     than using Seo.svelte, so the default set there does not reach it. -->
	<meta property="og:image" content={shareCard} />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta property="og:image:alt" content={t('home.shareImageAlt')} />
	<meta name="twitter:image" content={shareCard} />
	<meta name="twitter:image:alt" content={t('home.shareImageAlt')} />
	<meta name="twitter:card" content="summary_large_image" />
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html siteLd}
</svelte:head>

{#if showDashboard}
	<HomeDashboard {data} />
{:else}
	<HomeMarketing {data} />
{/if}
