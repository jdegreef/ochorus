<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import type { PlanRow } from '$lib/planRows';

	/**
	 * One reading-plan card: the title, a percent (or a ✓ "Finished"), a progress
	 * bar and the day tally. Shared by the home "Your plans" overview and the
	 * /reading page so a plan's resume card is drawn in exactly one place.
	 */
	let { row }: { row: PlanRow } = $props();
	const t = i18n.t;
</script>

<a
	href={localizeHref(`/plans/${row.slug}`)}
	class="block rounded-card border border-border bg-surface p-4 hover:border-accent hover:no-underline"
>
	<div class="flex items-baseline justify-between gap-3">
		<span class="min-w-0 truncate text-body font-semibold text-text">{row.title}</span>
		<span class="shrink-0 text-small tabular-nums text-muted">
			{#if row.finished}
				✓ {t('plans.finished')}
			{:else}
				{row.pct}%
			{/if}
		</span>
	</div>
	<div class="mt-2.5">
		<ProgressBar
			percent={row.pct}
			label="{row.title}: {row.done} {t('plans.of')} {row.total} {t('plans.days')}"
		/>
	</div>
	<p class="mt-1.5 text-small text-muted">
		{row.done} {t('plans.of')} {row.total} {t('plans.days')}
	</p>
</a>
