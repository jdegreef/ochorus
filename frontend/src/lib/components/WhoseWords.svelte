<script lang="ts">
	import { onMount } from 'svelte';
	import { SITE_URL } from '$lib/config';
	import { ApiError } from '$lib/api';
	import Arrow from '$lib/components/Arrow.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import QuoteCard from '$lib/components/QuoteCard.svelte';
	import QuoteText from '$lib/components/QuoteText.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { citeLine, getQuoteGame, quoteHref, type QuoteGame } from '$lib/library-public';
	import { share as shareSheet } from '$lib/platform';
	import {
		gameStreak,
		loadLog,
		recentDays,
		recordResult,
		resultLine,
		type GameLog
	} from '$lib/quoteGame';
	import { localToday } from '$lib/streak';

	/**
	 * "Whose words?" — the day's quotation, four writers, one guess
	 * (/quotes/game/). Everything here waits for the browser: the puzzle is the
	 * reader's LOCAL date ($lib/streak `localToday`, as /today keys its
	 * devotionals), so a prerendered puzzle would freeze on the deploy's day.
	 * The page around it prerenders; this fills in after mount.
	 */
	const t = i18n.t;

	let today = $state('');
	let game = $state<QuoteGame | null>(null);
	let status = $state<'loading' | 'ready' | 'unavailable' | 'error'>('loading');
	let log = $state<GameLog>({});

	const played = $derived(game && today ? log[today] : undefined);
	const answer = $derived(game?.choices.find((c) => c.slug === game?.answer));
	const streak = $derived(today ? gameStreak(log, today) : 0);
	const week = $derived(today ? recentDays(log, today) : []);
	const number = $derived(game ? t('game.number').replace('%n%', String(game.number)) : '');
	const streakText = $derived(
		(streak === 1 ? t('game.streakOne') : t('game.streakMany')).replace('%count%', String(streak))
	);

	async function load() {
		status = 'loading';
		today = localToday();
		log = loadLog();
		try {
			game = await getQuoteGame(today);
			status = 'ready';
		} catch (e) {
			// A 404 is "no puzzle today" (too few writers with portraits, or a
			// date the server won't answer yet) — not a failure to retry.
			status = e instanceof ApiError && e.status === 404 ? 'unavailable' : 'error';
		}
	}
	onMount(load);

	function guess(slug: string) {
		if (!game || played) return;
		log = recordResult(log, today, { n: game.number, guess: slug, right: slug === game.answer });
	}

	let copied = $state(false);
	async function shareResult() {
		if (!game || !played) return;
		const text = resultLine({
			title: t('game.title'),
			number,
			right: played.right,
			streak: streak > 1 ? streakText : ''
		});
		const url = `${SITE_URL}/quotes/game/`;
		if ((await shareSheet({ text, url })) !== 'unavailable') return;
		try {
			await navigator.clipboard.writeText(`${text}\n${url}`);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			/* no clipboard — nothing more to offer */
		}
	}
</script>

{#if status === 'loading'}
	<div class="game" aria-busy="true">
		<div class="skeleton quote-skel"></div>
	</div>
{:else if status === 'error'}
	<!-- Not EmptyState's `onRetry`, which re-runs the page load: the puzzle is
	     fetched after mount, so retrying means fetching it again. -->
	<EmptyState message={t('common.loadError')} art="failed">
		{#snippet action()}
			<button class="btn btn-primary" onclick={load}>{t('error.tryAgain')}</button>
		{/snippet}
	</EmptyState>
{:else if status === 'unavailable' || !game}
	<EmptyState message={t('game.unavailable')} />
{:else}
	<section class="game" aria-labelledby="game-prompt">
		<p class="eyebrow label">{number}</p>
		{#if !played}
			<blockquote class="line"><QuoteText text={game.quote.text} /></blockquote>
			<h2 id="game-prompt" class="section-label mt-6">{t('game.prompt')}</h2>
		{:else}
			<h2 id="game-prompt" class="verdict text-h3" aria-live="polite">
				<span class="mark" class:right={played.right}>
					<Icon name={played.right ? 'check' : 'close'} size={16} />
				</span>
				{(played.right ? t('game.right') : t('game.wrong')).replace('%name%', answer?.name ?? '')}
			</h2>
			<ul class="reveal">
				<QuoteCard quote={game.quote} authorName={answer?.name ?? ''} cite={citeLine(game.quote)} featured />
			</ul>
			<p class="mt-3 text-small">
				<a href={quoteHref(game.quote)}>{t('game.read')} <Arrow /></a>
			</p>
		{/if}

		<ul class="choices">
			{#each game.choices as c (c.slug)}
				{@const isAnswer = c.slug === game.answer}
				{@const isGuess = played?.guess === c.slug}
				<li>
					{#if played}
						<a
							class="choice"
							class:right={isAnswer}
							class:wrong={isGuess && !isAnswer}
							href={`/quotes/${c.slug}/`}
						>
							<Portrait slug={c.slug} name={c.name} url={c.photo_url} px={56} class="h-12 w-12" decorative tone={isAnswer ? 'color' : 'gray'} />
							<span class="name">{c.name}</span>
							{#if isAnswer}<span class="tick"><Icon name="check" size={16} /></span>{/if}
						</a>
					{:else}
						<button type="button" class="choice" onclick={() => guess(c.slug)}>
							<Portrait slug={c.slug} name={c.name} url={c.photo_url} px={56} class="h-12 w-12" decorative />
							<span class="name">{c.name}</span>
						</button>
					{/if}
				</li>
			{/each}
		</ul>

		{#if played}
			<div class="after">
				<div class="week" role="img" aria-label={streak ? `${t('game.lastWeek')}: ${streakText}` : t('game.lastWeek')}>
					{#each week as d (d.day)}
						<span class="sq {d.state}" aria-hidden="true"></span>
					{/each}
					{#if streak}<span class="text-small text-muted" aria-hidden="true">{streakText}</span>{/if}
				</div>
				<button type="button" class="btn btn-primary btn-sm" onclick={shareResult} aria-live="polite">
					{copied ? t('quotes.copied') : t('game.share')}
				</button>
			</div>
			<p class="mt-4 text-small text-muted">{t('game.tomorrow')}</p>
		{/if}
	</section>
{/if}

<style>
	.game {
		max-width: 44rem;
	}
	.label {
		color: var(--color-gold);
	}
	.line {
		margin: 0.6rem 0 0;
		font-family: var(--font-display, Georgia, serif);
		font-size: var(--fs-h2);
		line-height: 1.35;
		color: var(--color-text);
	}
	.quote-skel {
		height: 7rem;
		border-radius: var(--radius-card);
	}
	.verdict {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		margin: 0.6rem 0 0.9rem;
	}
	.mark {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.75rem;
		height: 1.75rem;
		flex-shrink: 0;
		border-radius: var(--radius-pill);
		background: var(--color-surface-2);
		color: var(--color-muted);
	}
	.mark.right {
		background: var(--color-accent-soft);
		color: var(--color-accent);
	}
	.reveal {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.choices {
		display: grid;
		gap: 0.6rem;
		margin: 0.75rem 0 0;
		padding: 0;
		list-style: none;
	}
	@media (min-width: 640px) {
		.choices {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	.choice {
		display: flex;
		width: 100%;
		min-height: 4rem;
		align-items: center;
		gap: 0.8rem;
		padding: 0.6rem 0.9rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
		color: var(--color-text);
		text-align: start;
		text-decoration: none;
		cursor: pointer;
	}
	button.choice:hover,
	button.choice:focus-visible {
		border-color: var(--color-accent);
	}
	.choice.right {
		border-color: var(--color-accent);
		background: var(--color-accent-soft);
	}
	.choice.wrong {
		opacity: 0.7;
	}
	.name {
		font-family: var(--font-display, Georgia, serif);
		font-size: var(--fs-h3);
	}
	.tick {
		margin-inline-start: auto;
		color: var(--color-accent);
	}
	.after {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		margin-top: 1.25rem;
	}
	.week {
		display: flex;
		align-items: center;
		gap: 0.3rem;
	}
	.sq {
		width: 1.1rem;
		height: 1.1rem;
		border-radius: var(--radius-sm);
		border: 1px solid var(--color-border);
		background: var(--color-surface);
	}
	.sq.right {
		border-color: var(--color-accent);
		background: var(--color-accent);
	}
	.sq.wrong {
		border-color: var(--color-muted);
		background: color-mix(in srgb, var(--color-muted) 35%, var(--color-surface));
	}
	.week .text-small {
		margin-inline-start: 0.4rem;
	}
</style>
