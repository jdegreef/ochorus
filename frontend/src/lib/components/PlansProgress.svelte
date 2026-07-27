<script lang="ts">
	import { onMount } from 'svelte';
	import { listPlans, type PlanSummary } from '$lib/library';
	import { planProgress } from '$lib/planProgress.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';

	/**
	 * Cross-plan progress overview: every plan the reader has started, each with
	 * its own progress bar. Complements "Today's reading" (which points at the
	 * single next action) by giving a portfolio view once more than one plan is
	 * in flight. Client-side only — the homepage is prerendered and this block is
	 * personal. Shown only when 2+ plans are underway, so a single-plan reader
	 * isn't shown a redundant one-row list.
	 */
	const t = i18n.t;

	interface Row {
		slug: string;
		title: string;
		total: number;
		done: number;
		pct: number;
		next: number | null;
	}
	let rows = $state<Row[]>([]);

	// Re-derive on every plan-progress mutation (a day marked on another tab, a
	// sign-in merge) so the bars stay live.
	const build = (plans: PlanSummary[]): Row[] => {
		void planProgress.ticks;
		return planProgress
			.started()
			.map(({ slug }) => plans.find((p) => p.slug === slug))
			.filter((p): p is PlanSummary => !!p)
			.map((p) => {
				const done = planProgress.doneDays(p.slug).length;
				const total = p.day_count;
				return {
					slug: p.slug,
					title: p.title,
					total,
					done,
					pct: total ? Math.round((done / total) * 100) : 0,
					next: planProgress.nextDay(p.slug, total)
				};
			});
	};

	let plans = $state<PlanSummary[]>([]);
	onMount(async () => {
		try {
			plans = await listPlans(getLang());
		} catch {
			/* plans are a bonus block — never break the homepage */
		}
	});
	$effect(() => {
		rows = plans.length ? build(plans) : [];
	});
</script>

{#if rows.length >= 2}
	<section class="mx-auto max-w-5xl px-5 pt-14">
		<div class="mb-4 flex items-end justify-between">
			<h2 class="text-h2">{t('home.yourPlans')}</h2>
			<a href={localizeHref('/plans')} class="text-small font-semibold text-accent"
				>{t('plans.all')} →</a
			>
		</div>
		<ul class="grid gap-3 sm:grid-cols-2">
			{#each rows as r (r.slug)}
				<li>
					<a
						href={localizeHref(`/plans/${r.slug}`)}
						class="block rounded-card border border-border bg-surface p-4 hover:border-accent hover:no-underline"
					>
						<div class="flex items-baseline justify-between gap-3">
							<span class="min-w-0 truncate text-body font-semibold text-text">{r.title}</span>
							<span class="shrink-0 text-small tabular-nums text-muted">
								{#if r.next === null}
									✓ {t('plans.finished')}
								{:else}
									{r.pct}%
								{/if}
							</span>
						</div>
						<div class="mt-2.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
							<div class="h-full rounded-full bg-accent" style="width: {r.pct}%"></div>
						</div>
						<p class="mt-1.5 text-small text-muted">
							{r.done} {t('plans.of')} {r.total} {t('plans.days')}
						</p>
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}
