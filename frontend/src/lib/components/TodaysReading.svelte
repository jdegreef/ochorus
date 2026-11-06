<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import { onMount } from 'svelte';
	import { todaysPlan, type PlanToday } from '$lib/todaysPlan';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';

	/**
	 * "Today's reading" — the next unread day of the reader's most recently
	 * started plan, or the first plan as an invitation to start
	 * (`$lib/todaysPlan`). Fetched CLIENT-SIDE (not in the page load): the
	 * homepage is prerendered, and this block is personal — baking it at build
	 * time would show every visitor the same non-personal state and require the
	 * plans API during the web build. Renders nothing until loaded, and nothing
	 * at all if plans are unavailable.
	 */
	const t = i18n.t;

	let today = $state<PlanToday | null>(null);

	onMount(async () => {
		try {
			today = await todaysPlan(getLang());
		} catch {
			/* plans are a bonus block — never break the homepage */
		}
	});
</script>

{#if today}
	<section class="page-col px-5 pt-14">
		<div
			class="flex flex-wrap items-center justify-between gap-4 rounded-card border border-border bg-surface p-6"
		>
			<div class="min-w-0">
				<p class="eyebrow mb-1 text-accent">
					{t('plans.todaysReading')}
				</p>
				<h2 class="text-h3 truncate text-text" title={today.chapterTitle || today.bookTitle}>
					{today.chapterTitle || today.bookTitle}
				</h2>
				<p class="mt-0.5 text-small text-muted">
					{today.plan.title} · {t('plans.day')} {today.day} {t('plans.of')} {today.plan.day_count}
				</p>
			</div>
			<div class="flex shrink-0 items-center gap-3">
				<a href={localizeHref(today.href)} class="btn btn-primary">
					{today.isStarted ? t('plans.continue') : t('plans.start')}
				</a>
				<a href={localizeHref('/plans')} class="text-small font-semibold text-accent">{t('plans.all')} <Arrow /></a>
			</div>
		</div>
	</section>
{/if}
