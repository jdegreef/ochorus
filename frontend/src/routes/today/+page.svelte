<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import DailyShelf from '$lib/components/DailyShelf.svelte';

	/** Every devotional's reading for today — where the home page's Today shelf
	 *  leads. The cards themselves are DailyShelf's. */
	const t = i18n.t;
</script>

<svelte:head>
	<title>{t('daily.title')} — Ochorus</title>
	<!-- Changes every day and is drawn in the browser: nothing for a crawler. -->
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader title={t('daily.title')} tagline={t('daily.subtitle')} />
	<div class="mt-8"><DailyShelf embedded /></div>
</div>
