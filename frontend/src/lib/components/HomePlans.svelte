<script lang="ts">
	import type { PlanSummary } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { lang } from '$lib/lang.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	/**
	 * Reading plans on the logged-out home (design review 2026-11, #21): "Plans"
	 * is in the top nav, and until now no plan appeared on the page. A plan is
	 * the easiest way into an old book — it sets the pace — so three of them,
	 * on the card /plans draws (`PlanShelfCard`), with a link to all of them.
	 * The picks come from the build's snapshot (`$lib/homeShelves`); none, and
	 * the section is not drawn.
	 */
	let { plans, total }: { plans: PlanSummary[]; total: number } = $props();
	const t = i18n.t;
</script>

{#if plans.length}
	<section class="page-col px-5 pt-14">
		<SectionHeader
			title={t('plans.title')}
			subtitle={t('plans.tagline')}
			href={localizeHref('/plans')}
			linkText={t('books.seeAll').replace('%n%', total.toLocaleString(lang.current))}
		/>
		<div class="grid items-stretch gap-x-6 gap-y-7 sm:grid-cols-2 lg:grid-cols-3">
			{#each plans as plan (plan.slug)}
				<PlanShelfCard {plan} headingLevel={3} />
			{/each}
		</div>
	</section>
{/if}
