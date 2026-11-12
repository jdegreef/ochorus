<script lang="ts">
	import EmbedToday from '$lib/components/EmbedToday.svelte';
	import { track } from '$lib/analytics';
	import { EMBED_EVENT } from '$lib/embed';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;

	// The church widget's page ($lib/embed): the card alone, inside embed.js's
	// iframe (or a pasted one) on a church's site. A click is counted by the
	// part followed, a label only, never a URL.
</script>

<svelte:head>
	<title>{t('home.todayTitle')} — Ochorus</title>
	<!-- Lives inside other sites' pages and changes every day: nothing for a
	     crawler. -->
	<meta name="robots" content="noindex" />
</svelte:head>

<EmbedToday report onopen={(part) => track(EMBED_EVENT, { part })} />

<style>
	/* The host page shows around the card, not Ochorus's paper ground: the
	   iframe is transparent wherever the card is not. */
	:global(body) {
		background: transparent;
		min-height: 0;
	}
	:global(.app-root) {
		min-height: 0;
	}
</style>
