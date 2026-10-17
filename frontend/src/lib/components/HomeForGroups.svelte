<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import { track } from '$lib/analytics';
	import { FOR_EYEBROW, FOR_LINKS, forIndexPath, forLabel, forPath } from '$lib/forLinks';
	import { PROMO_WORDS, promoLocale } from '$lib/forPromos';
	import { FOR_EVENT } from '$lib/forSections';
	import { lang } from '$lib/lang.svelte';

	/**
	 * The home page's "Ochorus for …" row: every group a chip, for the pastor,
	 * teacher or parent who arrives as a reader and is really a leader. Built
	 * from the footer's own list ($lib/forLinks), so a new group appears here
	 * too. Shown where the pages are written (English, French).
	 */
	const locale = $derived(promoLocale(lang.current));
</script>

{#if locale}
	<section class="page-col px-5 pt-14" aria-labelledby="home-for-heading" lang={locale}>
		<div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
			<h2 id="home-for-heading" class="text-h3">{PROMO_WORDS[locale].allLead}</h2>
			<a class="text-small font-semibold text-accent hover:underline" href={forIndexPath(locale)}
				>{PROMO_WORDS[locale].all} <Arrow /></a
			>
		</div>
		<ul class="mt-4 flex flex-wrap gap-2" aria-label="{FOR_EYEBROW[locale]}…">
			{#each FOR_LINKS as l (l.slug)}
				<li>
					<a
						class="chip"
						href={forPath(l.slug, locale)}
						onclick={() => track(FOR_EVENT, { group: l.slug, action: 'promo-home' })}>{forLabel(l, locale)}</a
					>
				</li>
			{/each}
		</ul>
	</section>
{/if}
