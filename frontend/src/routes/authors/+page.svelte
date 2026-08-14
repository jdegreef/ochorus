<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import type { PageData } from './$types';

	// There is no standalone /authors listing — the author directory lives at
	// /biographies. This page exists only as a PRERENDER ANCHOR, and it now
	// carries the links to make that true.
	//
	// It used to link nothing but /biographies, on the belief (stated here in a
	// comment) that "per-locale author detail pages are enumerated by
	// authors/[slug]'s own entries generator". They are not, and cannot be: an
	// entries generator returns route PARAMS, and the locale is not a route
	// param — it is a URL prefix resolved by the reroute hook. So `entries()`
	// only ever emits the canonical English URL, and every localized page
	// depends on the prerenderer CRAWLING a link to it.
	//
	// Two link sets were missing, and both were invisible from the code:
	//   * /biographies paginates client-side at PER_PAGE = 24, so the built HTML
	//     linked 24 of 35 writers. The 11 past page one were reachable only via a
	//     book page, and the 8 with no published works were reachable from
	//     nowhere — their localized pages never prerendered, while sitemap.xml
	//     advertised them in every locale. Google reported them as "Excluded by
	//     noindex", which is what the 200.html shell serves.
	//   * the era links sit inside `{:else if sort === 'era'}`, a client-side
	//     sort state, so NO built page in ANY locale contained one.
	//
	// Hence the full, unpaginated, unconditional list below. It is `noindex,
	// follow`: never indexed, always crawled — which is exactly what an anchor
	// is for. `prerenderCoverage.test.ts` fails the build if this ever stops
	// covering the sitemap.
	const t = i18n.t;
	let { data }: { data: PageData } = $props();

	onMount(() => goto(localizeHref('/biographies'), { replaceState: true }));
</script>

<svelte:head>
	<meta name="robots" content="noindex,follow" />
</svelte:head>

<p class="mx-auto max-w-xl px-5 py-24 text-center text-body text-muted">
	<a href={localizeHref('/biographies')}>{t('nav.biographies')}</a>
</p>

<!-- Crawl anchor. Hidden from readers (this page redirects on mount anyway) but
     present in the static HTML, which is all the prerenderer reads. Links go
     through $lib/href's localizeHref so they carry BOTH the locale prefix and
     the trailing slash — both routes set `trailingSlash = 'always'`, and the
     non-slash form is the one that falls through to the SPA shell. -->
<nav hidden aria-hidden="true">
	{#each data.slugs as slug (slug)}
		<a href={localizeHref(`/authors/${slug}`)}>{slug}</a>
	{/each}
	{#each data.eras as era (era)}
		<a href={localizeHref(`/biographies/era/${era}`)}>{era}</a>
	{/each}
</nav>
