<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import { track } from '$lib/analytics';
	import { FOR_LINKS, forIndexPath } from '$lib/forLinks';
	import { HOME_FOR_LINE, PROMO_WORDS, promoLocale } from '$lib/forPromos';
	import { FOR_EVENT } from '$lib/forSections';
	import { lang } from '$lib/lang.svelte';

	/**
	 * The home page's closing line for churches and ministries (design #27):
	 * one bold question, one sentence, one link to the /for/ hub — which lists
	 * every group page, so a leader still reaches theirs in a tap and the
	 * prerender crawler still finds each one (the footer links the hub too).
	 * The figure is the hub's own count. Shown where the pages are written
	 * (English, French); elsewhere nothing.
	 */
	const locale = $derived(promoLocale(lang.current));
</script>

{#if locale}
	<section class="page-col px-5 pt-14" aria-labelledby="home-for-lead" lang={locale}>
		<div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-4 border-y border-border py-6">
			<p class="max-w-2xl text-body text-muted">
				<strong id="home-for-lead" class="font-semibold text-text">{PROMO_WORDS[locale].allLead}</strong>
				{HOME_FOR_LINE[locale](FOR_LINKS.length)}
			</p>
			<a
				class="btn btn-ghost"
				href={forIndexPath(locale)}
				onclick={() => track(FOR_EVENT, { group: 'index', action: 'promo-home' })}
				>{PROMO_WORDS[locale].all} <Arrow /></a
			>
		</div>
	</section>
{/if}
