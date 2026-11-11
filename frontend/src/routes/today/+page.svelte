<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import { SITE_URL } from '$lib/config';
	import { collectionPage, fitList } from '$lib/seo';
	import type { DailyEntry } from '$lib/library-public';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import DailyShelf from '$lib/components/DailyShelf.svelte';

	/** Every devotional's reading for today — where the home page's Today shelf
	 *  leads. The cards themselves are DailyShelf's; this names them in the
	 *  head: whose readings they are (the title), the date and the books (the
	 *  description), and the day pages they lead to (a CollectionPage). */
	const t = i18n.t;

	let readings = $state<DailyEntry[]>([]);
	const dateLabel = new Date().toLocaleDateString(getLang(), { day: 'numeric', month: 'long' });

	const authors = $derived(readings.map((r) => r.book.author.name));
	const title = $derived(`${fitList(t('daily.title'), authors)} — Ochorus`);
	const description = $derived(
		readings.length
			? `${dateLabel} · ${t('daily.subtitle')}: ${readings.map((r) => r.book.title).join(', ')}.`
			: t('daily.subtitle')
	);
	const canonical = $derived(`${SITE_URL}${localizeHref('/today/')}`);
	const collectionLd = $derived(
		collectionPage({
			name: t('daily.title'),
			description,
			url: canonical,
			items: readings.map((r) => ({
				name: `${r.book.title} — ${r.label}`,
				url: localizeHref(`/today/${r.book.slug}/`)
			}))
		})
	);
</script>

<!-- No hreflang: which languages have a devotional for the day is only known
     once the shelf has loaded in THIS one, and an alternate naming a language
     with none would point at an empty page. -->
<Seo {title} {description} {canonical} hreflang={null} structuredData={[collectionLd]} />

<svelte:head>
	<!-- Still noindex: the page is client-only, so a crawler is served the SPA
	     shell (200.html), whose raw HTML already says noindex ($lib/fallbackShell)
	     before any of this head is drawn. Indexing it needs a prerendered shell. -->
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader title={t('daily.title')} tagline={t('daily.subtitle')} />
	<div class="mt-8"><DailyShelf embedded onreadings={(r) => (readings = r)} /></div>
</div>
