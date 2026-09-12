<script lang="ts">
	import { onMount } from 'svelte';
	import { listPlans, type PlanSummary } from '$lib/library-public';
	import { buildPlanRows, type PlanRow } from '$lib/planRows';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import PlanCard from '$lib/components/PlanCard.svelte';

	/**
	 * Cross-plan progress overview: every plan the reader has started, each with
	 * its own progress bar. Complements "Today's reading" (which points at the
	 * single next action) by giving a portfolio view once more than one plan is
	 * in flight. Client-side only — the homepage is prerendered and this block is
	 * personal. Shown only when 2+ plans are underway, so a single-plan reader
	 * isn't shown a redundant one-row list.
	 */
	const t = i18n.t;

	let plans = $state<PlanSummary[]>([]);
	onMount(async () => {
		try {
			plans = await listPlans(getLang());
		} catch {
			/* plans are a bonus block — never break the homepage */
		}
	});
	// Re-derives on every plan-progress mutation (buildPlanRows reads
	// planProgress.ticks), so the bars stay live across tabs and a sign-in merge.
	const rows = $derived<PlanRow[]>(plans.length ? buildPlanRows(plans) : []);
</script>

{#if rows.length >= 2}
	<section class="page-col px-5 pt-14">
		<SectionHeader
			title={t('home.yourPlans')}
			href={localizeHref('/plans')}
			linkText={t('plans.all')}
		/>
		<ul class="grid gap-3 sm:grid-cols-2">
			{#each rows as r (r.slug)}
				<li><PlanCard row={r} /></li>
			{/each}
		</ul>
	</section>
{/if}
