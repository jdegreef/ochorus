<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { jsonLd, hreflangAll } from '$lib/seo';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
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
			name: 'Ochorus',
			url: `${SITE_URL}/`,
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
			'@type': 'Organization',
			name: 'Ochorus',
			url: `${SITE_URL}/`,
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
	<!-- The site's most-linked page had a bare text card. The 1200×630 house
	     default gives it (and every share of the bare domain) a real image.
	     This page hand-rolls its head rather than using Seo.svelte, so the
	     default set there does not reach it. -->
	<meta property="og:image" content="{SITE_URL}/og/default.png" />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta name="twitter:image" content="{SITE_URL}/og/default.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html siteLd}
</svelte:head>

{#if showDashboard}
	<HomeDashboard {data} />
{:else}
	<HomeMarketing {data} />
{/if}
