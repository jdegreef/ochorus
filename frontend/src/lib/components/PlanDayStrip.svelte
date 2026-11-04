<script lang="ts">
	import type { PlanDetail } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import PlanDayDone from '$lib/components/PlanDayDone.svelte';

	/**
	 * The bar a reading wears when it is a plan's day (?plan=&day=): the plan,
	 * "Day N of M", and "Mark day done". One bar for every reading surface — a
	 * chapter, an article, a devotional's day page — so they cannot drift.
	 * `class` sets its spacing in the page that places it.
	 */
	let {
		plan,
		day,
		oncomplete,
		class: cls = ''
	}: {
		plan: Pick<PlanDetail, 'slug' | 'title' | 'day_count'>;
		day: number;
		oncomplete: () => void;
		class?: string;
	} = $props();
	const t = i18n.t;
</script>

<div
	class="flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-2 px-4 py-3 {cls}"
>
	<div class="min-w-0">
		<a href={localizeHref(`/plans/${plan.slug}`)} class="block truncate text-small font-semibold text-text hover:text-accent">
			{plan.title}
		</a>
		<span class="text-small text-muted">{t('plans.day')} {day} {t('plans.of')} {plan.day_count}</span>
	</div>
	<PlanDayDone slug={plan.slug} {day} {oncomplete} />
</div>
