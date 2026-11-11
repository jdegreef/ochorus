<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import DailyShelf from '$lib/components/DailyShelf.svelte';
	import TimePicker from '$lib/components/TimePicker.svelte';

	/** Every devotional's reading for today — where the home page's Today shelf
	 *  leads. The cards themselves are DailyShelf's. Under them, "How long do
	 *  you have?" (TimePicker): a chapter and a sermon that fit the time. */
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
	<div class="mt-12"><TimePicker /></div>
</div>
