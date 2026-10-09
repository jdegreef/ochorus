<script lang="ts">
	import { onMount } from 'svelte';
	import type { HubChallenge, SeriesSummary } from '$lib/library-public';
	import { challengeState } from '$lib/audienceHub';
	import { SITE_URL } from '$lib/config';
	import { allProgress } from '$lib/progress';
	import { readingActivity } from '$lib/readingActivity.svelte';
	import { currentStreak, localToday } from '$lib/streak';
	import { chapterPath } from '$lib/editionHref';
	import { splitSeriesTitle } from '$lib/series';
	import { seriesMeta } from '$lib/emblemNames';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import CoverStrip from './CoverStrip.svelte';
	import ProgressBar from './ProgressBar.svelte';
	import Icon from './Icon.svelte';
	import ShareButton from './ShareButton.svelte';

	/**
	 * A hub's daily devotional series, framed as a challenge: "Take the 30-day
	 * challenge", and — once the reader has begun — the day they've reached, a
	 * meter, their reading streak and one "Keep going". All of it from the
	 * reader's own progress and activity log, read after mount (the page is
	 * prerendered, so it bakes the not-yet-started band and a returning reader's
	 * place fills in), and again on `ochorus:sync` when an account's progress
	 * lands after the page did — the /series index's "Continue" does the same.
	 *
	 * "Do it with a friend" passes the series page on with an invitation — a
	 * challenge is easier kept with someone, and that needs no account.
	 */
	let {
		series,
		challenge,
		onstart,
		onshare
	}: {
		series: SeriesSummary;
		challenge: HubChallenge;
		onstart?: () => void;
		onshare?: () => void;
	} = $props();
	const t = i18n.t;

	let ticks = $state(0);
	onMount(() => {
		const bump = () => ticks++;
		bump();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	const volumes = $derived(series.books ?? []);
	// One read of the progress map per mount or sync, not one per volume.
	const records = $derived(
		new Map(ticks ? allProgress().filter((p) => p.kind === 'book').map((p) => [p.slug, p]) : [])
	);
	const place = $derived(challengeState(volumes, challenge.days, (slug) => records.get(slug) ?? null));
	const streak = $derived(ticks ? currentStreak(readingActivity.days(), localToday()) : 0);
	const name = $derived(splitSeriesTitle(series.title).name);
	const meta = $derived(seriesMeta(series.slug));
	const days = $derived(String(challenge.days));
	const dayLabel = $derived(
		t('audience.challengeDay').replace('%d%', String(place?.day ?? 0)).replace('%n%', days)
	);
</script>

{#if place}
	<section class="challenge mb-12" style:--shelf-hue={meta.accent} aria-labelledby="challenge-heading">
		<div class="challenge-covers" aria-hidden="true">
			<CoverStrip covers={series.covers} max={3} />
		</div>
		<div class="min-w-0">
			<p class="eyebrow text-accent">{name}</p>
			<h2 id="challenge-heading" class="mt-1 font-display text-h2 font-semibold leading-tight">
				{place.done
					? t('audience.challengeDone')
					: t('audience.challengeTitle').replace('%n%', days)}
			</h2>
			<p class="mt-2 max-w-xl text-small text-muted">
				{place.done
					? t('audience.challengeDoneLine')
					: t('audience.challengeLine').replace('%n%', days)}
			</p>
			{#if place.started && !place.done}
				<div class="mt-4 max-w-sm">
					<div class="mb-1.5 flex items-baseline justify-between gap-3 text-small">
						<span class="font-semibold text-text">{dayLabel}</span>
						{#if streak > 0}
							<span class="flex items-center gap-1 text-muted">
								<span class="text-gold"><Icon name="flame" size={16} /></span>
								{streak}
								{t('settings.streakLabel')}
							</span>
						{/if}
					</div>
					<ProgressBar percent={(place.day / challenge.days) * 100} label={`${name}: ${dayLabel}`} />
				</div>
			{/if}
			<div class="mt-5 flex flex-wrap items-center gap-3">
				{#if place.done}
					<a class="btn btn-ghost" href={localizeHref(`/series/${series.slug}/`)}>
						{t('audience.challengeSeries')}
					</a>
				{:else}
					<a
						class="btn btn-primary"
						href={localizeHref(chapterPath(place.slug, place.order, false))}
						onclick={onstart}
					>
						{place.started ? t('audience.challengeKeep') : t('audience.challengeStart')}
					</a>
					<ShareButton
						url={`${SITE_URL}${localizeHref(`/series/${series.slug}/`)}`}
						title={t('audience.challengeInvite').replace('%n%', days).replace('%s%', name)}
						label={t('audience.challengeShare')}
						showLabel
						{onshare}
					/>
				{/if}
			</div>
		</div>
	</section>
{/if}

<style>
	/* A banded card in the series' own hue — the emblem accent its series card
	   and "Continue your series" row wear — so the challenge reads as Anchored
	   (or Rooted), not as a new brand. */
	.challenge {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1.25rem;
		align-items: center;
		padding: 1.5rem;
		border: 1px solid var(--border);
		border-inline-start: 4px solid var(--shelf-hue);
		border-radius: var(--radius-card);
		background: linear-gradient(
			120deg,
			color-mix(in oklab, var(--shelf-hue) 14%, var(--surface)),
			var(--surface) 70%
		);
	}
	.challenge-covers {
		display: none;
	}
	@media (min-width: 640px) {
		.challenge {
			grid-template-columns: 9rem minmax(0, 1fr);
			gap: 2rem;
			padding: 1.75rem 2rem;
		}
		.challenge-covers {
			display: block;
		}
	}
</style>
