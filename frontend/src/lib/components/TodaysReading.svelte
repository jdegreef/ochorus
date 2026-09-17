<script lang="ts">
	import { onMount } from 'svelte';
	import { listPlans, getPlan, type PlanSummary } from '$lib/library-public';
	import { planProgress } from '$lib/planProgress.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';

	/**
	 * "Today's reading" — the next unread day of the reader's most recently
	 * started plan, or the first plan as an invitation to start. Fetched
	 * CLIENT-SIDE (not in the page load): the homepage is prerendered, and this
	 * block is personal — baking it at build time would show every visitor the
	 * same non-personal state and require the plans API during the web build.
	 * Renders nothing until loaded, and nothing at all if plans are unavailable.
	 */
	const t = i18n.t;

	interface Today {
		plan: PlanSummary;
		day: number;
		isStarted: boolean;
		chapterTitle: string;
		bookTitle: string;
		href: string;
	}
	let today = $state<Today | null>(null);

	onMount(async () => {
		try {
			const plans = await listPlans(getLang());
			if (!plans.length) return;
			const started = planProgress
				.started()
				.map(({ slug }) => plans.find((p) => p.slug === slug))
				.filter((p): p is NonNullable<typeof p> => !!p)
				.filter((p) => planProgress.nextDay(p.slug, p.day_count) !== null);
			// Fall back to a plan that still HAS a day left, not merely the first
			// in the catalog. `nextDay` returns null for a completed plan and the
			// `?? 1` below turned that into day 1 — so finishing the catalog's
			// first plan was rewarded with "Continue — Day 1 of 30", presenting a
			// 100%-complete plan as in progress at the beginning, right after the
			// reader's most satisfying moment.
			const unfinished = plans.filter(
				(p) => planProgress.nextDay(p.slug, p.day_count) !== null
			);
			const pick = started[0] ?? unfinished[0] ?? plans[0];
			const next = planProgress.nextDay(pick.slug, pick.day_count);
			const day = next ?? 1;

			const detail = await getPlan(pick.slug, getLang());
			const entry = detail.days.find((d) => d.day === day) ?? detail.days[0];
			if (!entry) return;
			today = {
				plan: pick,
				day: entry.day,
				// A finished plan is offered as a fresh START at day 1, never as a
				// continuation of something already complete.
				isStarted: next !== null && planProgress.isStarted(pick.slug),
				chapterTitle: entry.chapter_title,
				bookTitle: entry.book_title,
				href: `/books/${entry.book_slug}/${entry.chapter_order}?plan=${pick.slug}&day=${entry.day}`
			};
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
				<a href={localizeHref('/plans')} class="text-small font-semibold text-accent">{t('plans.all')} →</a>
			</div>
		</div>
	</section>
{/if}
