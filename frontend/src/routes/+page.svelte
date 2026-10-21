<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { OG_LOCALES, WEBSITE_ID, jsonLd, hreflangAll, publisherLd } from '$lib/seo';
	import { getLocale } from '$lib/paraglide/runtime';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { lang } from '$lib/lang.svelte';
	import { homeShareCardUrl } from '$lib/homeShareCard';
	import { onMount } from 'svelte';
	import { auth } from '$lib/auth.svelte';
	import HomeMarketing from '$lib/components/HomeMarketing.svelte';
	import HomeDashboard from '$lib/components/HomeDashboard.svelte';

	let { data } = $props();

	const t = i18n.t;

	// Site-level structured data: the WebSite and the publishing Organization,
	// linked by @id.
	const siteLd = jsonLd([
		{
			'@context': 'https://schema.org',
			'@type': 'WebSite',
			'@id': WEBSITE_ID,
			name: 'Ochorus',
			url: `${SITE_URL}/`,
			// The same organisation every book, chapter and sermon names as
			// publisher — one entity, linked by @id ($lib/seo publisherLd).
			publisher: publisherLd()
			// No SearchAction: Google retired the sitelinks search box it fed
			// (Nov 2024), and its target, /search?q=, is disallowed in robots.txt
			// — markup promising a URL the site tells crawlers not to fetch.
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
	// prerendered, and during the build `auth.enabled` is false (auth exists
	// only in the browser) and nothing has mounted, so the baked HTML is always
	// <HomeMarketing>. The dashboard swaps in client-side once the page
	// mounts — the same "personal blocks appear at hydration" trade the home
	// page already made (`mounted`, so hydration meets the HTML it was baked
	// with).
	//
	// It swaps in at MOUNT, from the session in storage (`auth.expectedUser`),
	// not once `auth.init()` has resolved: that waits on the supabase-js chunk
	// and, for a token past its hour, a refresh round-trip — seconds on a phone,
	// all of it spent behind the dashboard's skeleton. Nothing the dashboard
	// draws needs the token (its blocks are this device's cache and public
	// lists, re-read on the `ochorus:sync` the sign-in merge fires), so it waits
	// for none of it. Once the session has resolved it decides: a stored session
	// the client finds revoked goes back to the marketing page — rare, and a
	// swap the page made for every signed-in reader before.
	let mounted = $state(false);
	onMount(() => (mounted = true));
	const showDashboard = $derived(auth.enabled && mounted && !!auth.expectedUser);

	// Settled: mounted, so the page now shows what it will keep showing. Tell
	// the boot flag's CSS to reveal it — a frame later, once this render is on
	// the page.
	$effect(() => {
		if (!mounted) return;
		void showDashboard;
		const id = requestAnimationFrame(() =>
			document.documentElement.setAttribute('data-home-ready', '')
		);
		return () => cancelAnimationFrame(id);
	});

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

<!-- A signed-in reader's home is the dashboard, which exists only once the app
     runs; until it has mounted, app.html's boot flag keeps the prerendered
     page hidden behind .home-wait (app.css), drawn in the dashboard's shape —
     the hero band with its date and greeting, then a shelf — so the page
     arrives once, in place, over a likeness of itself rather than an empty
     ground. (A returning reader who is not signed in keeps the prerendered
     page, with the strip's space held: HomeMarketing .home-hold.) -->
<div class="home-root relative">
	<div class="home-wait" aria-hidden="true">
		<div class="home-wait-hero">
			<div class="page-col px-5 pb-8 pt-9 sm:pb-9 sm:pt-11">
				<div class="mb-3 h-4 w-52 rounded"></div>
				<div class="h-12 w-80 max-w-full rounded-md"></div>
				<div class="mt-4 h-6 w-40 rounded"></div>
				<div class="mt-6 h-3 w-32 rounded"></div>
				<div class="mt-2 h-6 w-56 max-w-full rounded"></div>
				<div class="mt-2 h-4 w-28 rounded"></div>
				<div class="mt-3 h-9 max-w-md rounded-md"></div>
			</div>
		</div>
		<div class="page-col px-5 pt-10">
			<div class="skeleton mb-6 h-8 w-56 rounded-md"></div>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<div class="skeleton h-36 rounded-card"></div>
				<div class="skeleton h-36 rounded-card"></div>
			</div>
		</div>
	</div>
	{#if showDashboard}
		<HomeDashboard {data} />
	{:else}
		<HomeMarketing {data} />
	{/if}
</div>

<style>
	/* The hero band as HomeHero draws it while its painting loads: the tint
	   it scrims with, and its lines as faint ink on it. */
	.home-wait-hero {
		background: var(--hero-tint);
	}
	.home-wait-hero div div {
		background: color-mix(in srgb, var(--hero-ink) 14%, transparent);
	}
</style>
