<script lang="ts">
	import type { PlanSummary } from '$lib/library-public';
	import { assetSrcset, assetUrl } from '$lib/assetUrl';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { coverGradient, coverSrcset } from '$lib/coverArt';
	import { tileFace } from '$lib/library-public';
	import { planProgress } from '$lib/planProgress.svelte';
	import { planMinutesPerDay } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { planMeta } from '$lib/emblemNames';
	import BookCover from '$lib/components/BookCover.svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';

	/**
	 * One plan on a shelf — /plans, the plan page's "More like this", and the
	 * topic and /for hubs (so a plan looks the same everywhere it is offered).
	 * Not `PlanCard`: that is the compact resume row of "Your plans".
	 *
	 * Led by the cover (design review #19, 2026-11): a plan is a journey through
	 * one or more books, so the books are what the card shows — one large cover,
	 * or two overlapping for a plan that reads several. Beside them the title,
	 * the length said once ("27 days · ~9 min/day"), and two lines of
	 * description. Boxless like the book card (design #1): no band, no per-card
	 * wash, no "DAYS 27" monogram repeating the length, no "Day 1 · …" teaser.
	 * A started plan shows its progress under the text (client-only state, so
	 * the prerender bakes the resting card).
	 */
	let { plan, headingLevel = 2 }: { plan: PlanSummary; headingLevel?: 2 | 3 } = $props();
	const t = i18n.t;
	// Looked up once per card, not per use: i18n.t is an uncached lookup.
	const OF = t('plans.of');
	const DAYS = t('plans.days');

	const covers = $derived(plan.covers.slice(0, 2));
	// The plan's curated accent: the hue of a cover with no colour of its own,
	// and of the emblem standing in for a plan with no covers.
	const meta = $derived(planMeta(plan.slug));
	const done = $derived(planProgress.doneDays(plan.slug).length);
	const started = $derived(planProgress.isStarted(plan.slug));
	/** Rounded minutes of reading in an average day of the plan. */
	const perDay = $derived(planMinutesPerDay(plan));
	/** The progress bar's accessible name — the visible caption, in words. */
	const dayLabel = $derived(`${plan.title}: ${done} ${OF} ${plan.day_count} ${DAYS}`);
</script>

<a class="plan-card group" href={localizeHref(`/plans/${plan.slug}`)}>
	<div class="plan-card-covers" class:two={covers.length > 1} aria-hidden="true">
		{#each covers as cover (cover.slug)}
			{@const face = tileFace(cover)}
			<div class="cover">
				{#if face}
					<!-- Drawn, not a bare image: a plate ground has no words. -->
					<BookCover book={face} rounded="" />
				{:else if cover.cover_url}
					{@const source = { src: assetUrl(cover.cover_url), srcset: assetSrcset(coverSrcset(cover.cover_url)) || undefined }}
					<img src={source.src} srcset={source.srcset} use:hydrateSrc={source} alt="" loading="lazy" />
				{:else}
					<div class="cover-fallback" style="background: {coverGradient(cover.cover_color || meta.accent)}"></div>
				{/if}
			</div>
		{:else}
			<!-- A plan whose books aren't in this language yet (every day an
			     article, say): its curated emblem holds the cover's place. -->
			<span class="emblem-chip" style="--chip-hue: {meta.accent}"><Emblem name={meta.emblem} /></span>
		{/each}
	</div>
	<div class="flex min-w-0 flex-col self-stretch">
		<svelte:element this={`h${headingLevel}`} class="plan-card-title">{plan.title}</svelte:element>
		<p class="mt-1 text-small text-muted">
			{plan.day_count} {DAYS}{#if perDay}<span class="sep">{' · '}</span>~{perDay} {t('plans.minPerDay')}{/if}
		</p>
		<p class="mt-1.5 line-clamp-2 text-small text-muted">{plan.description}</p>
		{#if started}
			<!-- Pushed to the foot, so started plans' bars line up across a row. -->
			<div class="mt-auto pt-2.5">
				<ProgressBar percent={(done / plan.day_count) * 100} label={dayLabel} />
				<p class="mt-1.5 text-small text-muted">
					{done === plan.day_count
						? t('plans.finished')
						: `${t('plans.day')} ${planProgress.nextDay(plan.slug, plan.day_count)} ${OF} ${plan.day_count}`}
				</p>
			</div>
		{/if}
	</div>
</a>

<style>
	/* Boxless, as the book card is: the covers sit on the page ground and the
	   card's one hover is the book card's rise. */
	.plan-card {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		height: 100%;
		padding: 0.25rem;
		border-radius: var(--radius-card);
		color: inherit;
		transition: transform var(--duration-fast);
	}
	.plan-card:hover {
		text-decoration: none;
		transform: translateY(-2px);
	}
	@media (prefers-reduced-motion: reduce) {
		.plan-card,
		.plan-card:hover {
			transform: none;
		}
	}
	.plan-card-title {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.25;
		color: var(--text);
		transition: color var(--duration-fast);
	}
	.plan-card:hover .plan-card-title {
		color: var(--accent);
	}

	/* The cover slot is one size whether it holds one book or two, so every
	   card's text starts on the same line down a column. */
	.plan-card-covers {
		position: relative;
		flex-shrink: 0;
		width: 5.5rem;
		aspect-ratio: 3 / 4;
	}
	.cover {
		width: 100%;
		aspect-ratio: 3 / 4;
		border-radius: 0.3rem;
		overflow: hidden;
		background: var(--surface);
		box-shadow: var(--shadow-card);
	}
	/* Two books: the first stands behind at the top start, the second in front,
	   lower and toward the end — both upright (a book is never drawn on a
	   slant — coverStraight.test.ts). Logical offsets, so RTL mirrors it. */
	.two .cover {
		position: absolute;
		width: 74%;
	}
	.two .cover:first-child {
		top: 0;
		inset-inline-start: 0;
	}
	.two .cover:last-child {
		bottom: 0;
		inset-inline-end: 0;
		box-shadow: var(--shadow-card), var(--shadow-popover);
	}
	.cover img,
	.cover-fallback {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	/* Block-level, so the auto margins centre it in the cover slot (an inline
	   box ignores them). */
	.emblem-chip {
		--chip-size: 4rem;
		display: flex;
		margin: 0.75rem auto 0;
	}
</style>
