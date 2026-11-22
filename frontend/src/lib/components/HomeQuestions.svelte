<script lang="ts">
	import QandA from '$lib/components/QandA.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { homeQa } from '$lib/homeQa';
	import { faqPage } from '$lib/seo';
	import { getLocale } from '$lib/paraglide/runtime';

	// "Questions about Ochorus" on the logged-out home ($lib/homeQa). The
	// FAQPage JSON-LD rides with the visible section, so the markup only ever
	// describes answers that are on the page.
	const t = i18n.t;
	const items = $derived(homeQa(t, getLocale()));
	const ld = $derived(faqPage(items));
</script>

<svelte:head>
	<!-- Built by faqPage() (jsonLd-escaped) from the catalogue's own strings. -->
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html ld}
</svelte:head>

<!-- A plain wrapper: QandA's own <section> is already the landmark, named by
     its heading. Labelling this one too gave screen readers two identical
     "Questions about Ochorus" regions (bug review 2026-11-22, #32). -->
<div class="page-col px-5 pt-14">
	<QandA {items} title={t('home.qa.title')} headingClass="section-heading" />
</div>
