<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import { track } from '$lib/analytics';
	import { FOR_LINKS, forIndexPath, forLabel, forPath } from '$lib/forLinks';
	import { HOME_FOR_LINE, PROMO_WORDS, promoLocale } from '$lib/forPromos';
	import { FOR_EVENT } from '$lib/forSections';
	import { lang } from '$lib/lang.svelte';

	/**
	 * The home page's closing band for churches and ministries (design #27,
	 * then review 2026-11 #25): one question, one sentence, three named group
	 * pages and one solid link to the /for/ hub — which lists
	 * every group page, so a leader still reaches theirs in a tap and the
	 * prerender crawler still finds each one (the footer links the hub too).
	 * The figure is the hub's own count. Shown where the pages are written
	 * (English, French); elsewhere nothing.
	 */
	const locale = $derived(promoLocale(lang.current));

	// Three groups named outright (design review 2026-11, #25), so a leader
	// sees their own setting before the hub: the ones the line itself names,
	// "from small groups to prison chaplaincy", and schools. Shown in the
	// hub's own order (FOR_LINKS).
	const EXAMPLES = ['small-groups', 'schools', 'prison-ministry'];
	const examples = FOR_LINKS.filter((l) => EXAMPLES.includes(l.slug));
</script>

{#if locale}
	<section class="page-col px-5 pt-14" aria-labelledby="home-for-lead" lang={locale}>
		<div class="for-band">
			<h2 id="home-for-lead" class="text-h3">{PROMO_WORDS[locale].allLead}</h2>
			<p class="mt-1 max-w-2xl text-body text-muted">{HOME_FOR_LINE[locale](FOR_LINKS.length)}</p>
			<div class="mt-4 flex flex-wrap items-center gap-2">
				{#each examples as l (l.slug)}
					<a
						class="for-pill"
						href={forPath(l.slug, locale)}
						onclick={() => track(FOR_EVENT, { group: l.slug, action: 'promo-home' })}
						>{forLabel(l, locale)} <Arrow /></a
					>
				{/each}
				<a
					class="btn btn-primary btn-solid sm:ms-auto"
					href={forIndexPath(locale)}
					onclick={() => track(FOR_EVENT, { group: 'index', action: 'promo-home' })}
					>{PROMO_WORDS[locale].all} <Arrow /></a
				>
			</div>
		</div>
	</section>
{/if}

<style>
	/* A band of its own, on the accent's soft ground, rather than one line
	   between hairlines that read as a footnote. */
	.for-band {
		padding: 1.25rem 1.5rem;
		border: 1px solid var(--accent-soft-border);
		border-radius: var(--radius-card);
		background: var(--accent-soft);
	}
	.for-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		min-height: 2.25rem;
		padding: 0.25rem 0.85rem;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-pill);
		background: var(--surface);
		color: var(--text);
		font-size: var(--fs-small);
		text-decoration: none;
	}
	.for-pill:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
</style>
