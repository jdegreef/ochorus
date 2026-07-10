<script lang="ts">
	import type { PlanDetail } from '$lib/library';
	import { planProgress } from '$lib/planProgress.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	let { data } = $props();
	const plan = $derived<PlanDetail>(data.plan);
	const t = i18n.t;

	const started = $derived(planProgress.isStarted(plan.slug));
	const next = $derived(planProgress.nextDay(plan.slug, plan.day_count));
	const doneCount = $derived(planProgress.doneDays(plan.slug).length);

	const dayHref = (day: number) => {
		const d = plan.days.find((x) => x.day === day);
		return d ? localizeHref(`/books/${d.book_slug}/${d.chapter_order}?plan=${plan.slug}&day=${day}`) : '#';
	};
</script>

<svelte:head><title>{plan.title} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<nav class="mb-5 text-small text-muted" aria-label="Breadcrumb">
		<a href={localizeHref('/plans')} class="hover:text-text">{t('plans.title')}</a>
		<span> › </span>
		<span class="text-text">{plan.title}</span>
	</nav>

	<h1 class="text-h1 mb-2">{plan.title}</h1>
	<p class="mb-6 max-w-xl text-body text-muted">{plan.description}</p>

	{#if next !== null}
		<a href={dayHref(next)} class="btn btn-primary" onclick={() => planProgress.start(plan.slug)}>
			{started ? t('plans.continue') : t('plans.start')} — {t('plans.day')}
			{next} {t('plans.of')} {plan.day_count}
		</a>
	{:else}
		<p class="btn btn-ghost pointer-events-none inline-block">✓ {t('plans.finished')}</p>
	{/if}

	{#if started}
		<div class="mt-5 h-1.5 max-w-md overflow-hidden rounded-full bg-surface-2">
			<div
				class="h-full rounded-full bg-accent"
				style="width: {Math.round((doneCount / plan.day_count) * 100)}%"
			></div>
		</div>
	{/if}

	<ol class="mt-8 divide-y divide-border">
		{#each plan.days as d (d.day)}
			{@const done = planProgress.isDone(plan.slug, d.day)}
			{@const isNext = d.day === next}
			<li>
				<a
					href={dayHref(d.day)}
					class="flex items-center gap-4 py-3.5 hover:no-underline"
					onclick={() => planProgress.start(plan.slug)}
				>
					<span
						class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-small font-semibold"
						class:border-accent={isNext}
						class:text-accent={isNext && !done}
						class:border-border={!isNext}
						class:bg-accent={done}
						class:text-white={done}
						class:text-muted={!done && !isNext}
					>
						{done ? '✓' : d.day}
					</span>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-body text-text" class:font-semibold={isNext}>
							{d.chapter_title || `${t('plans.day')} ${d.day}`}
						</span>
						<span class="block text-small text-muted">{d.book_title}</span>
					</span>
					{#if isNext}
						<span class="shrink-0 text-small font-semibold text-accent">{t('plans.today')}</span>
					{/if}
				</a>
			</li>
		{/each}
	</ol>
</div>
