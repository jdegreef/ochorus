<script lang="ts">
	import type { PlanSummary } from '$lib/library';
	import { planProgress } from '$lib/planProgress.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	let { data } = $props();
	const plans = $derived<PlanSummary[]>(data.plans);
	const t = i18n.t;
</script>

<svelte:head><title>{t('plans.title')} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<h1 class="text-h1 mb-2">{t('plans.title')}</h1>
	<p class="mb-8 max-w-xl text-body text-muted">{t('plans.tagline')}</p>

	{#if plans.length === 0}
		<p class="text-small text-muted">{t('plans.none')}</p>
	{/if}

	<div class="space-y-4">
		{#each plans as plan (plan.slug)}
			{@const done = planProgress.doneDays(plan.slug).length}
			{@const started = planProgress.isStarted(plan.slug)}
			<a
				href={localizeHref(`/plans/${plan.slug}`)}
				class="block rounded-card border border-border p-5 hover:bg-surface-2 hover:no-underline"
			>
				<div class="flex items-baseline justify-between gap-3">
					<h2 class="text-h3 text-text">{plan.title}</h2>
					<span class="shrink-0 text-small text-muted">
						{plan.day_count} {t('plans.days')}
					</span>
				</div>
				<p class="mt-1 text-small text-muted">{plan.description}</p>
				{#if started}
					<div class="mt-3">
						<div class="h-1.5 overflow-hidden rounded-full bg-surface-2">
							<div
								class="h-full rounded-full bg-accent"
								style="width: {Math.round((done / plan.day_count) * 100)}%"
							></div>
						</div>
						<p class="mt-1.5 text-[0.78rem] text-muted">
							{done === plan.day_count
								? t('plans.finished')
								: `${t('plans.day')} ${planProgress.nextDay(plan.slug, plan.day_count)} ${t('plans.of')} ${plan.day_count}`}
						</p>
					</div>
				{/if}
			</a>
		{/each}
	</div>
</div>
